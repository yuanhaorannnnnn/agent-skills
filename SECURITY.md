# Security Policy

## Supported versions

项目尚未发布稳定版本。目前仅维护默认分支的最新代码，不承诺旧 commit、fork 或第三方修改版本的安全更新。

## Reporting a vulnerability

请使用 GitHub Security Advisory 的私密报告功能联系维护者。若该入口不可用，请创建一个不含漏洞细节的 issue，请求维护者提供私下联系渠道。不要公开 PoC，也不要附带真实 credentials、客户数据或不必要的敏感日志。

报告请包含：受影响路径或 skill、可复现条件、潜在影响、最小 PoC，以及已知缓解措施。维护者会先确认收到报告，再协调披露与修复；在修复发布前请勿公开细节。

重点关注安装/更新脚本、符号链接处理、命令执行、外部内容摄取、凭据泄露和绕过人工确认或 gate 的行为。
