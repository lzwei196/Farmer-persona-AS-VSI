# GitHub上传说明

上传统一仓库目录本身的内容，包括隐藏的`.github`、`.gitignore`和`.gitattributes`。保留`data`、`src`、`scripts`、`figures`、`prompts`、`config`和`docs`的目录结构，不要按某一张图拆开上传。

先按README运行文件校验。使用Git上传时，在本目录初始化仓库、提交文件，再把远程地址设为你实际建立的GitHub仓库。不要把示例地址当作真实仓库标识。

```bash
git init
git add .
git commit -m "Add unified research data and code package"
git branch -M main
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

原始完整调查文件通过随包的官方获取脚本下载，不需要把960MB原始解压目录加入Git。已纳入的紧凑去标识调查输入可以直接重跑性状分析。`reproduced/`、本地缓存和凭据文件已在`.gitignore`中排除。

真正公开前，核对CITATION作者身份和模型生成数据许可。发布后再用真实GitHub/归档标识更新论文数据和代码声明。不要重新上传旧的单图更正包；本版本已经统一整合。
