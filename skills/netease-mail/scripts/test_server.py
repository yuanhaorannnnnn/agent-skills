import unittest
import asyncio
from unittest.mock import patch
from email.message import EmailMessage
import server


class FakeImap:
    def __init__(self): self.calls = []; self.capabilities = ('IMAP4REV1', 'MOVE')
    def select(self, folder, readonly=True): self.calls.append(('select', folder, readonly)); return 'OK', [b'1']
    def response(self, name): return 'UIDVALIDITY', [b'42']
    def uid(self, *args):
        self.calls.append(args)
        if args[0] == 'SEARCH': return 'OK', [b'1 2 3']
        if args[0] == 'FETCH' and args[2] == '(RFC822.SIZE)': return 'OK', [b'1 (RFC822.SIZE 30)']
        if args[0] == 'FETCH': return 'OK', [(b'1 (BODY[] {30}', b'From: a@example.org\r\nSubject: Hi\r\n\r\nHello')]
        return 'OK', [b'']
    def logout(self): pass


class FakeSmtp:
    def __init__(self, *args, **kwargs): self.payload = b''
    def login(self, *args): pass
    def sendmail(self, sender, recipients, payload): self.payload = payload; self.recipients = recipients; return {}
    def quit(self): pass


class TestMail(unittest.TestCase):
    def test_search_and_read_are_peek_and_uid_checked(self):
        c = FakeImap()
        with patch.object(server, 'connect', return_value=c):
            result = server.search_emails(limit=2)
            self.assertEqual([x['id'] for x in result['items']], ['SU5CT1g:42:3', 'SU5CT1g:42:2'])
            self.assertEqual(result['next_before_uid'], 2)
            self.assertTrue(all(x[2] is True for x in c.calls if x[0] == 'select'))
            self.assertTrue(any('BODY.PEEK' in str(x) for x in c.calls))
            self.assertEqual(server.read_email('INBOX', 'SU5CT1g:42:1')['body'], 'Hello')
            with self.assertRaisesRegex(ValueError, 'UIDVALIDITY changed'): server.read_email('INBOX', 'SU5CT1g:41:1')
            with self.assertRaisesRegex(ValueError, 'another folder'): server.read_email('Other', 'SU5CT1g:42:1')

    def test_send_bcc_removed_and_one_call(self):
        smtp = FakeSmtp()
        with patch.object(server, 'account', return_value=('user@163.com', 'secret', ('imap.163.com', 'smtp.163.com'))), patch.object(server.smtplib, 'SMTP_SSL', return_value=smtp):
            result = server.send_email(['to@example.org'], 'Subject', 'Body', bcc=['secret@example.org'])
        self.assertEqual(result['status'], 'accepted')
        self.assertIn('secret@example.org', smtp.recipients)
        self.assertNotIn(b'Bcc:', smtp.payload)
        self.assertNotIn(b'secret@example.org', smtp.payload)

    def test_ambiguous_send_is_not_retried(self):
        smtp = FakeSmtp()
        with patch.object(smtp, 'sendmail', side_effect=TimeoutError) as send, patch.object(server, 'account', return_value=('user@163.com', 'secret', ('imap.163.com', 'smtp.163.com'))), patch.object(server.smtplib, 'SMTP_SSL', return_value=smtp):
            result = server.send_email(['to@example.org'], 'Subject', 'Body')
        self.assertEqual(result['status'], 'uncertain')
        self.assertEqual(send.call_count, 1)

    def test_size_limit_before_body_fetch(self):
        c = FakeImap()
        with patch.object(c, 'uid', return_value=('OK', [b'1 (RFC822.SIZE 99999999)'])) as fetch:
            with self.assertRaisesRegex(ValueError, 'exceeds'): server._fetch(c, '1')
        self.assertEqual(fetch.call_count, 1)

    def test_id_sent_when_server_advertises_it(self):
        c = FakeImap()
        c.capabilities = ('IMAP4REV1', 'ID')
        c.login = lambda *args: ('OK', [b''])
        c._simple_command = lambda *args: c.calls.append(args) or ('OK', [b''])
        with patch.object(server, 'account', return_value=('user@163.com', 'secret', ('imap.163.com', 'smtp.163.com'))), patch.object(server.imaplib, 'IMAP4_SSL', return_value=c):
            self.assertIs(server.connect(), c)
        self.assertTrue(any(call[0] == 'ID' for call in c.calls))

    def test_move_uses_advertised_string_capability(self):
        c = FakeImap()
        with patch.object(server, 'connect', return_value=c):
            result = server.move_email('INBOX', 'SU5CT1g:42:1', 'Archive')
        self.assertEqual(result['status'], 'unconfirmed')
        self.assertTrue(any(call[0] == 'MOVE' for call in c.calls))

    def test_forward_with_attachment_is_blocked_before_smtp(self):
        msg = EmailMessage()
        msg['From'] = 'a@example.org'; msg['Subject'] = 'subject'; msg.set_content('body')
        msg.add_attachment(b'data', maintype='application', subtype='octet-stream', filename='a.bin')
        with patch.object(server, 'connect', return_value=FakeImap()), patch.object(server, '_fetch', return_value=msg.as_bytes()), patch.object(server, '_send') as send:
            with self.assertRaisesRegex(ValueError, 'faithful forwarding'):
                server.forward_email('INBOX', 'SU5CT1g:42:1', ['to@example.org'])
            send.assert_not_called()

    def test_forward_with_inline_binary_is_blocked_before_smtp(self):
        msg = EmailMessage()
        msg['From'] = 'a@example.org'; msg['Subject'] = 'subject'; msg.set_content('body')
        msg.add_attachment(b'data', maintype='image', subtype='png', disposition='inline', cid='<image>')
        with patch.object(server, 'connect', return_value=FakeImap()), patch.object(server, '_fetch', return_value=msg.as_bytes()), patch.object(server, '_send') as send:
            with self.assertRaisesRegex(ValueError, 'faithful forwarding'):
                server.forward_email('INBOX', 'SU5CT1g:42:1', ['to@example.org'])
            send.assert_not_called()

    def test_send_draft_rejects_without_draft_flag(self):
        c = FakeImap()
        with patch.object(server, 'connect', return_value=c), patch.object(server, '_send') as send:
            with self.assertRaisesRegex(ValueError, 'Draft flag'):
                server.send_draft('INBOX', 'SU5CT1g:42:1')
            send.assert_not_called()

    def test_flag_store_ok_without_matching_uid_is_unconfirmed(self):
        c = FakeImap()
        with patch.object(server, 'connect', return_value=c):
            result = server.update_flags('INBOX', 'SU5CT1g:42:1', 'seen', True)
        self.assertEqual(result['status'], 'unconfirmed')

    def test_draft_append_timeout_and_logout_do_not_mask_result(self):
        c = FakeImap()
        c.append = lambda *args: (_ for _ in ()).throw(TimeoutError())
        c.logout = lambda: (_ for _ in ()).throw(TimeoutError())
        with patch.object(server, 'account', return_value=('user@163.com', 'secret', ('imap.163.com', 'smtp.163.com'))), patch.object(server, 'connect', return_value=c):
            result = server.create_draft('Drafts', ['to@example.org'], 'subject', 'body')
        self.assertEqual(result['status'], 'uncertain')
        self.assertIn('before retrying', result['note'])

    def test_resent_headers_are_rejected_before_smtp(self):
        msg = EmailMessage()
        msg['From'] = 'user@163.com'; msg['To'] = 'to@example.org'
        msg['Resent-Bcc'] = 'secret@example.org'; msg.set_content('body')
        with patch.object(server.smtplib, 'SMTP_SSL') as smtp:
            with self.assertRaisesRegex(ValueError, 'Resent headers'):
                server._send(msg, 'user@163.com', ['to@example.org'])
        smtp.assert_not_called()

    def test_mcp_send_annotations(self):
        tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
        for name in ('send_email', 'reply_email', 'forward_email', 'send_draft'):
            self.assertTrue(tools[name].annotations.destructiveHint, name)
        self.assertFalse(tools['create_draft'].annotations.destructiveHint)
        self.assertTrue(tools['read_email'].annotations.readOnlyHint)

    def test_update_draft_preserves_mime_and_thread_headers(self):
        c = FakeImap()
        c.uid = lambda *args: ('OK', [b'1 (UID 1 FLAGS (\\Draft))'])
        sent = []
        c.append = lambda *args: sent.append(args[-1]) or ('OK', [b''])
        original = EmailMessage()
        original['From'] = 'user@163.com'; original['To'] = 'to@example.org'; original['Subject'] = 'Old'
        original['Message-ID'] = '<old@example.org>'; original['In-Reply-To'] = '<reply@example.org>'
        original['References'] = '<root@example.org> <reply@example.org>'
        original.set_content('Original body')
        original.add_attachment(b'file contents', maintype='application', subtype='octet-stream', filename='proof.bin')
        with patch.object(server, 'account', return_value=('user@163.com', 'secret', ('imap.163.com', 'smtp.163.com'))), patch.object(server, 'connect', return_value=c), patch.object(server, '_fetch', return_value=original.as_bytes()):
            result = server.update_draft('INBOX', 'SU5CT1g:42:1', subject='New')
            with self.assertRaisesRegex(ValueError, 'Body edits'):
                server.update_draft('INBOX', 'SU5CT1g:42:1', body='Edited')
        self.assertEqual(result['status'], 'created_replacement')
        self.assertTrue(result['original_retained'])
        self.assertEqual(len(sent), 1)
        saved = server._message(sent[0])
        self.assertEqual(saved['Subject'], 'New')
        self.assertEqual(saved['In-Reply-To'], '<reply@example.org>')
        self.assertEqual(saved['References'], '<root@example.org> <reply@example.org>')
        self.assertEqual(list(saved.iter_attachments())[0].get_payload(decode=True), b'file contents')
        self.assertIn('Original body', saved.get_body(preferencelist=('plain',)).get_content())
        self.assertNotEqual(saved['Message-ID'], '<old@example.org>')

    def test_update_draft_rejects_non_draft_and_marks_timeout_uncertain(self):
        c = FakeImap()
        c.uid = lambda *args: ('OK', [b'1 (UID 1 FLAGS (\\Seen))'])
        original = EmailMessage(); original['From'] = 'user@163.com'; original['To'] = 'to@example.org'; original['Subject'] = 'Old'; original.set_content('Body')
        with patch.object(server, 'account', return_value=('user@163.com', 'secret', ('imap.163.com', 'smtp.163.com'))), patch.object(server, 'connect', return_value=c), patch.object(server, '_fetch', return_value=original.as_bytes()):
            with self.assertRaisesRegex(ValueError, 'not a verified draft'):
                server.update_draft('INBOX', 'SU5CT1g:42:1', subject='New')
            c.uid = lambda *args: ('OK', [b'1 (UID 1 FLAGS (\\Draft))'])
            c.append = lambda *args: (_ for _ in ()).throw(TimeoutError())
            result = server.update_draft('INBOX', 'SU5CT1g:42:1', subject='New')
        self.assertEqual(result['status'], 'uncertain')
        self.assertTrue(result['original_retained'])

    def test_thread_is_header_linked_incomplete_and_readonly(self):
        c = FakeImap()
        headers = {'1': b'Message-ID: <root@example.org>\r\nSubject: Same\r\n\r\n',
                   '2': b'Message-ID: <reply@example.org>\r\nReferences: <root@example.org>\r\n\r\n',
                   '3': b'Message-ID: <unrelated@example.org>\r\nSubject: Same\r\n\r\n'}
        def uid(*args):
            c.calls.append(args)
            if args[0] == 'SEARCH': return 'OK', [b'1 2 3']
            return 'OK', [(b'header', headers[args[1]])]
        c.uid = uid
        with patch.object(server, 'connect', return_value=c): result = server.read_thread('INBOX', 'SU5CT1g:42:1')
        self.assertFalse(result['complete'])
        self.assertEqual({item['id'] for item in result['items']}, {'SU5CT1g:42:1', 'SU5CT1g:42:2'})
        self.assertTrue(all('BODY.PEEK' in str(call) for call in c.calls if call[0] == 'FETCH'))

    def test_header_injection_rejected(self):
        with patch.object(server, 'account', return_value=('user@163.com', 'secret', ('imap.163.com', 'smtp.163.com'))):
            with self.assertRaises(ValueError): server.send_email(['a@example.org\r\nBcc: x@example.org'], 'a', 'b')

if __name__ == '__main__': unittest.main()
