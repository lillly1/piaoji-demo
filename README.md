# 票迹 · 国内机票真实展示价测试版

票迹现在包含一个基于 FastAPI、Craw4AI 和 Chromium 的动态后端。搜索时，后端按城市与日期访问第三方公开航线页，只返回当次成功识别的公开展示价；不再生成或回退到模拟价格。

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Flillly1%2Fpiaoji-demo)

## 当前真实数据范围

- 首个数据适配器：携程移动端公开航线页
- 支持：单程、1–9 人、今天起 90 天内、常用国内民航城市
- 返回：出发/到达时间、机场、公开展示价、数据来源和抓取时间
- 失败行为：显示“暂无实时报价”，不会展示模拟价格
- 缓存：同一航线和日期 5 分钟，减少重复访问
- 最终价格仍需在第三方平台页面再次核对

## 部署

仓库根目录的 `render.yaml` 定义了新加坡区域的 Render Docker Web Service。容器使用 Crawl4AI 官方镜像并通过 `/health` 接受健康检查。

GitHub Pages 只能展示静态前端，不能运行 Craw4AI。完整动态版本应通过 Render 生成的 `onrender.com` 地址访问。
