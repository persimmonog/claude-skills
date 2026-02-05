# Cookies.txt 说明

## 如何获取 YouTube Cookies.txt

由于 YouTube 有机器人检测，本工具需要使用您的 YouTube cookies 来下载音频。

### 步骤：

1. **安装浏览器扩展**

   在 Chrome 浏览器中安装扩展：
   **"Get cookies.txt LOCALLY"**

   或访问：https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbanldgopeb

2. **导出 cookies**

   - 打开 YouTube 并登录您的账号
   - 点击浏览器工具栏中的扩展图标
   - 选择 "Get cookies.txt LOCALLY"
   - 点击 "Current Site" 或 "All"
   - 点击 "Export" 下载 cookies.txt 文件

3. **放置文件**

   将下载的 cookies.txt 文件重命名为 `cookies.txt`，并放到此技能的根目录（与 config.json 同级）。

### 安全提示

- cookies.txt 包含您的登录信息，请勿分享给他人
- 如果下载失败，可以重新导出 cookies.txt（cookies 会定期过期）
- 建议定期更新 cookies.txt 以确保下载功能正常

### 验证

运行以下命令测试 cookies 是否有效：

```bash
python3 scripts/download_video.py "https://www.youtube.com/watch?v=TEST_VIDEO_ID"
```

如果成功下载，说明 cookies 配置正确。
