# Contributing

欢迎提交可复用、边界明确且能够验证的 agent skill 改进。

1. 先开 issue 描述使用场景、触发方式、预期输出和风险边界；小型文档修正可直接提交 PR。
2. 修改或新增 skill 时，同步更新 `manifest.yaml` 和 README 的 Skill 目录。每个 manifest 名称必须对应 `skills/<name>/SKILL.md`。
3. 不要提交 credentials、客户数据、私有对话、运行日志或机器相关绝对路径。
4. 为行为变化添加最小测试或 gate；保持脚本可在仓库根目录复现。
5. 提交 PR 前运行：

```bash
node scripts/install.mjs doctor
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s skills/acquisition/tests -p 'test_*.py'
python3 -m unittest discover -s skills/passdown/tests -p 'test_*.py'
git diff --check
```

PR 请说明变更范围、验证结果、兼容性影响和仍未验证的内容。维护者可能要求缩小 scope，或拒绝无法安全自动化的工作流。
