# 发布后验证清单

`gh repo create ... --push` 返回成功，只证明命令跑完了。下面每一条都要**读回来**核对，不能把"推送时的输出"当证据。

占位符：`<owner>` / `<name>` / `<branch>`。`<branch>` 是**远端的默认分支**——新建仓库通常是 `main`，老仓库可能是 `master`，先确认真实值，别假设，下面的 `git diff` 和 `gh api` 都依赖它。

## 1. 远端仓库元数据

```bash
gh repo view <owner>/<name> --json url,visibility,defaultBranchRef,isEmpty,licenseInfo
gh api repos/<owner>/<name> --jq '{description, topics}'
```

判据：`visibility` 是 `PUBLIC`；`isEmpty` 为 `false`；`defaultBranchRef.name` 等于你实际推的那条分支；`licenseInfo` 是你放的那个许可证；`description` 与 `topics` 已补上——空 description 的仓库等于没进检索。

## 2. 远端引用与本地一致

```bash
git remote -v                        # origin 指向本仓库
git ls-remote origin                 # 远端确实有这条分支的 ref
git fetch origin
git diff HEAD origin/<branch>        # 期望：无输出
git rev-parse HEAD origin/<branch>   # 两个 hash 相同
```

`git diff` 一有输出就停下查。常见原因：默认分支不是你推的这条；本地还有未提交或未跟踪的文件（`--push` 不推未跟踪文件）。

## 3. 远端对象数 = 本地文件数

```bash
git ls-files | wc -l

gh api repos/<owner>/<name>/git/trees/<branch>?recursive=1 \
  --jq '[.tree[] | select(.type=="blob")] | length'
```

两个数字应相等。少了 → 有文件没提交，或被 `.gitignore` 排掉（README 里引用的图最常这样漏，正文对得上、图是坏的）；多了 → 推了不该推的东西（临时文件、构建产物、本地笔记）。

## 4. README 与安装命令

```bash
grep -n 'npx skills add\|git clone' README.md README_CN.md
gh api repos/<owner>/<name>/readme --jq '.name'
```

判据：README 里的安装命令是你**真跑过**的（或显式标了"未实机验证"），且命令里的 `<owner>/<name>` 拼写正确。这一步的价值在于失败最静默——外面的人第一步就失败，但他们不会回来告诉你，只会关掉页面。

## 5. 全历史密钥扫描

这一步本工作区已有专门的技能（`git-secret-audit`），直接用它，不要临时 grep 了事——它覆盖的正是这里最难的部分：**不是扫当前文件，而是扫所有历史对象**。

要点记在这里，免得被略过：

- **删掉文件不等于删掉历史。** 任何曾经 `git add` 并提交过的凭据都还在对象库里，`git log -p`、`git cat-file` 都取得到。
- 扫描要覆盖**全部提交**，包括已经不在默认分支上的那些。
- 真发现了泄漏，顺序是**先轮换凭据，再考虑重写历史**——历史里的东西在轮换之前一直是有效的。

## 6. 悬空与丢失对象

```bash
git fsck --lost-found
```

期望结果是空，或只有正常无害的 `dangling` 提示。要看清它到底列了什么：里面可能躺着你 rebase 前提交过、以为删掉的内容（凭据、内部文档）。任何真实对象被列出来，都按待处理看待。

## 7. 页面级人工核对（读不回来，只能看）

- 打开 `https://github.com/<owner>/<name>`：README 第一屏的图**加载出来了吗**（路径大小写、`docs/` 是否被 `.gitignore` 排掉）。
- 仓库页右侧是否识别出了许可证。
- 技能目录下的 `references/` 文件是否都在——拍平安装之后那些相对链接还成立吗。
- 如果 README 提供了会写 `~/.agents` 的安装方式（`npx skills add`）：要么在**干净环境**里实跑一次，要么明确标"未实机验证"。

## 8. 记一笔

把"这次验过什么、什么没验、为什么"写进提交信息或维护说明。下一次同步开源副本（见 SKILL §9）要靠它才知道哪些差异是刻意的、哪些是漏的。
