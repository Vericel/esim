# esim 编辑器支持

esim 的 `*.tc` 和 `*.rules` 文件使用标准 YAML 语法。本目录只把这两种
后缀关联到编辑器已有的 YAML 语法，不另外定义 esim 专用语法。

## VS Code

从本仓库根目录打开 VS Code 时，[workspace 设置](../../.vscode/settings.json)
已经自动生效。

要在其他项目或用户级配置中使用，打开 VS Code 命令面板，执行
`Preferences: Open User Settings (JSON)`，然后把
[`tools/editors/vscode/settings.json`](vscode/settings.json) 中的两个关联合并到已有
`files.associations` 中：

```json
"files.associations": {
  "*.rules": "yaml",
  "*.tc": "yaml"
}
```

语法高亮使用 VS Code 的 YAML language mode。如果还需要 YAML 诊断、格式化或
schema 支持，可以另行安装所选的 YAML 扩展；文件关联本身不依赖扩展。

打开 `*.tc` 或 `*.rules` 后，VS Code 右下角的语言模式应显示
`YAML`。

## Vim 和 gVim

[`tools/editors/vim-esim`](vim-esim/) 是一个遵循 Vim native package 目录结构的最小
filetype 插件。它对 Vim 和 gVim 同时生效。

Linux/WSL/macOS 用户可以复制该目录：

```bash
mkdir -p ~/.vim/pack/esim/start
cp -R tools/editors/vim-esim ~/.vim/pack/esim/start/esim-yaml
```

Windows gVim 用户把 `tools/editors/vim-esim` 复制到：

```text
%USERPROFILE%\vimfiles\pack\esim\start\esim-yaml
```

目标目录中应保留 `ftdetect/esim.vim` 这一层结构。重启 Vim/gVim 并打开
`*.tc` 或 `*.rules` 后，执行：

```vim
:set filetype?
```

预期输出为 `filetype=yaml`。卸载时删除上述 `esim-yaml` 目录即可。

## Release 分发

`.vscode/settings.json` 和完整的 `tools/editors/` 目录应随源码 release 保留。Python wheel
和 wheelhouse 只包含运行时内容，不是编辑器插件的安装介质；如果 release 只分发
wheelhouse，需要额外附上 `tools/editors/` 目录。
