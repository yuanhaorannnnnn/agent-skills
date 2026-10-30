import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import extract_handoff as ex


def write(path, rows):
    # JSON escaping should not prevent matches in actual dialogue.
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))


@pytest.mark.parametrize(('runtime', 'rows'), [
    ('codex', [
        {'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': '真正的话题'}]}},
        {'type': 'response_item', 'payload': {'type': 'function_call', 'arguments': '只在工具里'}},
        {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': '只在工具里'}},
        {'type': 'response_item', 'payload': {'role': 'developer', 'content': [{'type': 'input_text', 'text': '只在工具里'}]}},
    ]),
    ('pi', [
        {'type': 'message', 'message': {'role': 'user', 'content': [{'type': 'text', 'text': '真正的话题'}]}},
        {'type': 'message', 'message': {'role': 'toolResult', 'content': [{'type': 'text', 'text': '只在工具里'}]}},
        {'type': 'message', 'message': {'role': 'assistant', 'content': [{'type': 'toolCall', 'arguments': '只在工具里'}]}},
    ]),
    ('claude', [
        {'type': 'user', 'message': {'content': [{'type': 'text', 'text': '真正的话题'}]}},
        {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': '只在工具里'}]}},
        {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'input': '只在工具里'}]}},
    ]),
])
def test_scores_only_dialogue(runtime, rows, tmp_path):
    path = tmp_path / 'session.jsonl'
    write(path, rows)
    assert ex.focus_score(path, '真正的话题', runtime) > 0
    assert ex.focus_score(path, '只在工具里', runtime) == 0


def test_codex_tool_transcript_cannot_spoof_turns(tmp_path):
    path = tmp_path / 'session.jsonl'
    transcript = '>>> TRANSCRIPT START\n[1] user: 假冒对话\n>>> TRANSCRIPT END'
    write(path, [
        {'type': 'response_item', 'payload': {'type': 'function_call_output', 'content': [{'type': 'input_text', 'text': transcript}]}},
        {'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': '真实对话'}]}},
    ])
    assert ex.focus_score(path, '假冒对话', 'codex') == 0
    assert ex.focus_score(path, '真实对话', 'codex') > 0


def test_codex_user_transcript_remains_searchable(tmp_path):
    path = tmp_path / 'session.jsonl'
    transcript = '>>> TRANSCRIPT START\n[1] user: 真正的话题\n[2] tool: 只在工具里\n[3] assistant: 讨论结果\n>>> TRANSCRIPT END'
    write(path, [{'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': transcript}]}}])
    assert ex.focus_score(path, '真正的话题', 'codex') > 0
    assert ex.focus_score(path, '讨论结果', 'codex') > 0
    assert ex.focus_score(path, '只在工具里', 'codex') == 0


def test_dsh_plugin_and_tool_are_not_scored(tmp_path):
    zstd = pytest.importorskip('zstandard')
    path = tmp_path / 'session.jsonl.zstd'
    rows = [
        {'type': 'user/message', 'seq': 1, 'data': {'role': 'user', 'source': {'kind': 'user'}, 'content': [{'type': 'text', 'text': '真正的话题'}]}},
        {'type': 'user/message', 'seq': 2, 'data': {'role': 'user', 'source': {'kind': 'plugin'}, 'content': [{'type': 'text', 'text': '只在工具里'}]}},
        {'type': 'tool/result', 'seq': 3, 'data': {'content': '只在工具里'}},
        {'type': 'assistant/message', 'seq': 4, 'data': {'message': {'role': 'assistant', 'content': [{'type': 'reasoning', 'text': '只在工具里'}]}}},
    ]
    path.write_bytes(zstd.ZstdCompressor().compress(''.join(json.dumps(row) + '\n' for row in rows).encode()))
    assert ex.focus_score(path, '真正的话题', 'dsh') > 0
    assert ex.focus_score(path, '只在工具里', 'dsh') == 0


def test_keyword_cli_excludes_tool_only_session(tmp_path):
    import os
    import subprocess
    project = tmp_path / 'project'
    project.mkdir()
    folder = tmp_path / '.codex' / 'sessions' / '2026' / '10' / '30'
    folder.mkdir(parents=True)
    meta = {'type': 'session_meta', 'payload': {'cwd': str(project)}}
    good, noise = folder / 'good.jsonl', folder / 'noise.jsonl'
    write(good, [meta, {'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': '找到真实线索'}]}}])
    write(noise, [meta, {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': '找到真实线索'}}])
    env = dict(os.environ, HOME=str(tmp_path))
    cmd = [sys.executable, str(Path(ex.__file__)), '--former', 'codex', '--dir', str(project), '--focus', '真实线索', '--retriever', 'keyword', '--json']
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
    out = json.loads(result.stdout)
    assert out['session_files'] == [str(good)]
    assert out['turns'][0]['text'] == '找到真实线索'


def test_codex_user_event_transcript_remains_searchable(tmp_path):
    path = tmp_path / 'session.jsonl'
    text = '>>> TRANSCRIPT START\n[1] user: 用户历史\n[2] assistant: 确认结果\n>>> TRANSCRIPT END'
    write(path, [{'type': 'event_msg', 'payload': {'type': 'user_message', 'message': text}}])
    assert ex.focus_score(path, '确认结果', 'codex') > 0


def test_corpus_ranking_filters_common_term_and_preserves_explicit_term(tmp_path):
    candidates = []
    for index, text in enumerate(['Wiki 语义检索排障', 'Wiki 图片记录', 'Wiki 项目计划', 'Wiki 文章归档', '其他记录']):
        path = tmp_path / f'{index}.jsonl'
        write(path, [{'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': text}]}}])
        candidates.append({'path': path, 'runtime': 'codex'})
    status = ex.rank_keyword_candidates(candidates, 'Wiki 语义检索')
    assert 'wiki' not in status['active_terms']
    assert [i for i, c in enumerate(candidates) if c['focus_score'] > 0] == [0]
    ex.rank_keyword_candidates(candidates, 'Wiki')
    assert [i for i, c in enumerate(candidates) if c['focus_score'] > 0] == [0, 1, 2, 3]


def test_missing_specific_identifier_does_not_become_broad_match(tmp_path):
    candidates = []
    for index, text in enumerate(['Wiki 时间回放和实体关系', 'Wiki 检索', 'Wiki 其他', 'Wiki 原话']):
        path = tmp_path / f'{index}.jsonl'
        write(path, [{'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': text}]}}])
        candidates.append({'path': path, 'runtime': 'codex'})
    status = ex.rank_keyword_candidates(candidates, 'Memvid 时间回放和实体关系 Wiki')
    assert status['mandatory_terms'] == ['memvid']
    assert all(c['focus_score'] == 0 for c in candidates)


def test_multiple_terms_must_cooccur_in_a_turn(tmp_path):
    candidates = []
    for index, texts in enumerate([['模型巡检完毕', '这次升级通过'], ['本轮巡检无升级']]):
        path = tmp_path / f'{index}.jsonl'
        write(path, [{'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': text}]}} for text in texts])
        candidates.append({'path': path, 'runtime': 'codex'})
    ex.rank_keyword_candidates(candidates, '巡检 升级')
    assert candidates[0]['focus_score'] == 0
    assert candidates[1]['focus_score'] > 0


def test_optional_tokenizer_missing_has_literal_fallback(tmp_path, monkeypatch):
    import builtins
    real_import = builtins.__import__
    def absent(name, *args, **kwargs):
        if name == 'jieba':
            raise ImportError('missing optional tokenizer')
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', absent)
    path = tmp_path / 'session.jsonl'
    write(path, [{'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': 'Wiki 语义检索'}]}}])
    candidates = [{'path': path, 'runtime': 'codex'}]
    status = ex.rank_keyword_candidates(candidates, 'Wiki 语义检索')
    assert status['tokenizer'] == 'literal_fallback'
    assert candidates[0]['focus_score'] > 0


def test_explicit_single_stopword_or_character_is_searchable():
    assert ex.keyword_tokens('增加')[0] == ['增加']
    assert ex.keyword_tokens('车')[0] == ['车']


def test_best_keyword_turn_survives_budget():
    turns = [{'role': 'assistant', 'text': ('背景内容 ' * 200) + str(i)} for i in range(18)]
    turns[7]['text'] = '关于相应问题的证据 ' + ('详细说明 ' * 200)
    turns[7]['keyword_hit'] = True
    result, stats = ex.budget_turns(turns, '不重合的提问', 500)
    assert stats['budget_applied']
    assert any(turn.get('keyword_hit') for turn in result)


def test_meaningful_verb_is_not_dropped_from_a_broad_query(tmp_path):
    candidates = []
    for index, text in enumerate(['Wiki 增加条目', 'Wiki 图片', 'Wiki 计划', 'Wiki 记录', '其他']):
        path = tmp_path / f'{index}.jsonl'
        write(path, [{'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': text}]}}])
        candidates.append({'path': path, 'runtime': 'codex'})
    status = ex.rank_keyword_candidates(candidates, 'Wiki 增加')
    assert '增加' in status['active_terms']
    assert [i for i, c in enumerate(candidates) if c['focus_score'] > 0] == [0]


def test_automation_prompt_ignored_but_identifier_links_to_results(tmp_path):
    candidates = []
    prompt = ('Automation: 定时任务巡检\nAutomation ID: automation-7\n'
              'Automation memory: /somewhere/memory.md\nLast run: never\n\n'
              '给 Wiki 增加语义检索，涉及错误的任务说明。')
    rows = [
        {'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': prompt}]}},
        {'type': 'response_item', 'payload': {'role': 'assistant', 'content': [{'type': 'output_text', 'text': '运行状态写入失败，缺少 key。'}]}},
    ]
    path = tmp_path / 'task.jsonl'
    write(path, rows)
    candidates.append({'path': path, 'runtime': 'codex'})
    for i in range(5):
        path = tmp_path / f'other-{i}.jsonl'
        write(path, [{'type': 'response_item', 'payload': {'role': 'user', 'content': [{'type': 'input_text', 'text': '其他事项'}]}}])
        candidates.append({'path': path, 'runtime': 'codex'})
    ex.rank_keyword_candidates(candidates, 'Wiki 语义检索')
    assert candidates[0]['focus_score'] == 0
    ex.rank_keyword_candidates(candidates, 'automation-7 状态写入失败')
    assert candidates[0]['focus_score'] > 0
    assert candidates[0]['keyword_ordinals'] == [1]
    assert ex.automation_context({'role':'user', 'text':prompt}) == {'name':'定时任务巡检', 'id':'automation-7'}
    assert ex.automation_context({'role':'user', 'text':'Automation: 这个词我想查一下'}) is None


def test_adjacent_distinct_rare_terms_recalled_without_general_word_join(tmp_path):
    candidates = []
    discussions = [
        [('user', '讨论玉米栽培'), ('assistant', '灌溉制度要调整。')],
        [('user', '增加目录'), ('assistant', '开始检索')],
    ] + [[('user', '增加目录和检索入口')] for _ in range(8)]
    for i, turns in enumerate(discussions):
        path = tmp_path / f'{i}.jsonl'
        write(path, [{'type':'response_item', 'payload':{'role':role, 'content':[{'type':'input_text' if role=='user' else 'output_text', 'text':text}]}} for role,text in turns])
        candidates.append({'path':path, 'runtime':'codex'})
    ex.rank_keyword_candidates(candidates, '玉米 灌溉')
    assert candidates[0]['focus_score'] > 0
    assert candidates[0]['keyword_match'] == 'adjacent'
    assert candidates[0]['keyword_ordinals'] == [0, 1]
    ex.rank_keyword_candidates(candidates, '增加 检索')
    assert candidates[1]['focus_score'] == 0


def test_cli_keeps_automation_result_metadata_and_prompt(tmp_path):
    import os
    import subprocess
    project = tmp_path / 'project'
    project.mkdir()
    folder = tmp_path / '.codex' / 'sessions' / '2026' / '10' / '30'
    folder.mkdir(parents=True)
    path = folder / 'task.jsonl'
    prompt = ('Automation: 定时巡检\nAutomation ID: automation-7\nAutomation memory: /memory\n'
              'Last run: never\n\n重复任务说明：额外细节')
    write(path, [
        {'type':'session_meta','payload':{'cwd':str(project)}},
        {'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':prompt}]}},
        {'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':'巡检结果：没有升级。'}]}},
    ])
    cmd = [sys.executable,str(Path(ex.__file__)),'--former','codex','--dir',str(project),'--focus','automation-7','--retriever','keyword','--json']
    result = subprocess.run(cmd, env=dict(os.environ, HOME=str(tmp_path)), capture_output=True, text=True, check=True)
    out = json.loads(result.stdout)
    assert out['automation_contexts'][0]['id'] == 'automation-7'
    assert [t['text'] for t in out['turns']] == [prompt, '巡检结果：没有升级。']
    assert out['automation_contexts'][0]['instruction_status'] == 'complete'


def test_adjacent_terms_remain_searchable_in_small_scope(tmp_path):
    path = tmp_path / 'session.jsonl'
    write(path, [
        {'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':'确认玉米的种植'}]}},
        {'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':'灌溉计划已经落实。'}]}},
    ])
    candidates = [{'path':path,'runtime':'codex'}]
    ex.rank_keyword_candidates(candidates, '玉米 灌溉')
    assert candidates[0]['keyword_match'] == 'adjacent'


def test_automation_identifier_uses_result_context_to_break_ties(tmp_path):
    prompt = ('Automation: 定时巡检\nAutomation ID: automation-7\nAutomation memory: /memory\nLast run: never\n\nignored')
    candidates = []
    for i, text in enumerate(['运行状态写入失败', '本轮无更新', '状态写入失败记录', '状态写入失败记录', '状态写入失败记录']):
        path = tmp_path / f'{i}.jsonl'
        rows = []
        if i < 2:
            rows.append({'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':prompt}]}})
        rows.append({'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':text}]}})
        write(path, rows)
        candidates.append({'path':path,'runtime':'codex'})
    ex.rank_keyword_candidates(candidates, 'automation-7 状态写入失败')
    assert candidates[0]['focus_score'] == candidates[1]['focus_score'] > 0
    assert candidates[0]['keyword_context_matches'] > candidates[1]['keyword_context_matches']


def test_cli_adjacent_match_returns_both_source_turns(tmp_path):
    import os
    import subprocess
    project = tmp_path / 'project'
    project.mkdir()
    folder = tmp_path / '.codex' / 'sessions' / '2026' / '10' / '30'
    folder.mkdir(parents=True)
    path = folder / 'session.jsonl'
    write(path, [
        {'type':'session_meta','payload':{'cwd':str(project)}},
        {'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':'玉米种植问题'}]}},
        {'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':'灌溉需要调整。'}]}},
    ])
    cmd = [sys.executable,str(Path(ex.__file__)),'--former','codex','--dir',str(project),'--focus','玉米 灌溉','--retriever','keyword','--json']
    result = subprocess.run(cmd, env=dict(os.environ, HOME=str(tmp_path)), capture_output=True, text=True, check=True)
    out = json.loads(result.stdout)
    assert out['candidates'][0]['keyword_match'] == 'adjacent'
    assert len(out['turns']) == 2 and all(turn.get('keyword_hit') for turn in out['turns'])


def test_automation_without_result_is_discoverable_as_metadata(tmp_path):
    prompt = ('Automation: 定时巡检\nAutomation ID: automation-7\nAutomation memory: /memory\nLast run: never\n\n任务说明')
    path = tmp_path / 'session.jsonl'
    write(path, [{'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':prompt}]}}])
    candidates = [{'path':path,'runtime':'codex'}]
    ex.rank_keyword_candidates(candidates, 'automation-7')
    assert candidates[0]['focus_score'] > 0
    assert candidates[0]['keyword_match'] == 'metadata'
    assert 'keyword_ordinals' not in candidates[0]


def test_existing_zvec_metadata_rejects_automation_prompt_preview(tmp_path):
    prompt = ('Automation: 定时巡检\nAutomation ID: automation-7\nAutomation memory: /memory\nLast run: never\n\n指令')
    (tmp_path / 'metadata.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in [
        {'id':'prompt','role':'user','text_preview':prompt},
        {'id':'result','role':'assistant','text_preview':'实际巡检结果'},
    ]))
    assert set(ex._load_zvec_metadata(tmp_path)) == {'result'}


def test_truncated_zvec_automation_preview_is_filtered(tmp_path):
    preview = 'Automation: 定时巡检\nAutomation ID: automation-7\nAutomation memory: /very/long/path'
    (tmp_path / 'metadata.jsonl').write_text(json.dumps({'id':'prompt','role':'user','text_preview':preview}, ensure_ascii=False)+'\n')
    assert ex._load_zvec_metadata(tmp_path) == {}


def test_adjacent_keyword_pair_survives_normal_budget():
    turns = [{'role':'assistant','text':f'第{i}条背景 ' + '信息' * 400} for i in range(20)]
    turns[7] = {'role':'user','text':'玉米种植 ' + '说明' * 400,'keyword_hit':True}
    turns[8] = {'role':'assistant','text':'灌溉调整 ' + '建议' * 400,'keyword_hit':True}
    selected, status = ex.budget_turns(turns, '玉米 灌溉', 600)
    assert status['budget_applied']
    assert sum(bool(t.get('keyword_hit')) for t in selected) == 2


def test_automation_identifier_is_exact_for_metadata_and_dialogue(tmp_path):
    candidates = []
    for identifier in ('automation-7', 'automation-70'):
        path = tmp_path / f'{identifier}.jsonl'
        prompt = (f'Automation: 定时巡检\nAutomation ID: {identifier}\nAutomation memory: /memory\n'
                  'Last run: never\n\n只读巡检；不要发送邮件。')
        write(path, [
            {'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':prompt}]}},
            {'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':f'{identifier} 巡检完成'}]}},
        ])
        candidates.append({'path':path,'runtime':'codex'})
    ex.rank_keyword_candidates(candidates, 'automation-7')
    assert candidates[0]['focus_score'] > 0
    assert candidates[1]['focus_score'] == 0


def test_explicit_file_handoff_preserves_automation_constraints(tmp_path):
    import subprocess
    path = tmp_path / 'session.jsonl'
    prompt = ('Automation: 测试巡检\nAutomation ID: automation-7\nAutomation memory: /memory\n'
              'Last run: never\n\n只读巡检；不要发送邮件。')
    write(path, [
        {'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':prompt}]}},
        {'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':'已检查。'}]}},
    ])
    result = subprocess.run([sys.executable, str(Path(ex.__file__)), '--former','codex','--file',str(path),'--json'], capture_output=True,text=True,check=True)
    data = json.loads(result.stdout)
    assert '不要发送邮件' in data['turns'][0]['text']
    assert data['automation_contexts'][0]['instruction_status'] == 'complete'


def test_truncated_automation_instructions_are_flagged(tmp_path):
    import subprocess
    path = tmp_path / 'session.jsonl'
    prompt = ('Automation: 测试巡检\nAutomation ID: automation-7\nAutomation memory: /memory\n'
              'Last run: never\n\n' + '前文' * 200 + '不要发送邮件' + '后文' * 200)
    write(path, [{'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':prompt}]}}])
    result = subprocess.run([sys.executable,str(Path(ex.__file__)),'--former','codex','--file',str(path),'--max-tokens','30','--json'],capture_output=True,text=True,check=True)
    data = json.loads(result.stdout)
    assert data['automation_contexts'][0]['instruction_status'] in ('truncated','omitted')
    assert data['automation_contexts'][0]['session_file'] == str(path)


def test_legacy_focus_score_also_matches_identifiers_exactly(tmp_path):
    path = tmp_path / 'session.jsonl'
    write(path, [{'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':'automation-70 已完成'}]}}])
    assert ex.focus_score(path, 'automation-7', 'codex') == 0
    assert ex.focus_score(path, 'automation-70', 'codex') > 0


def test_automation_constraints_survive_recent_and_explicit_session(tmp_path):
    import os
    import subprocess
    project = tmp_path / 'project'
    project.mkdir()
    folder = tmp_path / '.codex' / 'sessions' / '2026' / '10' / '30'
    folder.mkdir(parents=True)
    path = folder / 'rollout-task-id.jsonl'
    prompt = ('Automation: 测试巡检\nAutomation ID: automation-7\nAutomation memory: /memory\n'
              'Last run: never\n\n只读巡检；不要发送邮件。')
    write(path, [
        {'type':'session_meta','payload':{'cwd':str(project)}},
        {'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':prompt}]}},
        {'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':'巡检已完成。'}]}},
    ])
    base = [sys.executable,str(Path(ex.__file__)),'--former','codex','--dir',str(project),'--json']
    for extra in ([], ['--session','task-id']):
        out = subprocess.run(base+extra,env=dict(os.environ,HOME=str(tmp_path)),capture_output=True,text=True,check=True)
        data = json.loads(out.stdout)
        assert any('不要发送邮件' in turn['text'] for turn in data['turns'])
        assert data['automation_contexts'][0]['instruction_status'] == 'complete'


@pytest.mark.parametrize(('text','expected'), [
    ('completed automation-7.', 1),
    ('automation-7: 已完成', 1),
    ('automation-70 已完成', 0),
    ('automation-7-extra 已完成', 0),
    ('automation-7x 已完成', 0),
])
def test_identifier_boundary_preserves_sentence_punctuation(text, expected):
    assert ex.keyword_occurrences('automation-7', text.lower()) == expected
