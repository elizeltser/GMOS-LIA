vim.lsp.start({
  name = "clangd",
  cmd = { "clangd" },
  root_dir = vim.fs.root(0, { "compile_commands.json", ".clangd", ".git" }),
})
