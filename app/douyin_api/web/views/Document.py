from pywebio.output import popup, put_markdown, put_html, put_text, put_link
from app.douyin_api.web.views.ViewsUtils import ViewsUtils

t = ViewsUtils().t


# API文档弹窗/API documentation pop-up
def api_document_pop_window():
    with popup(t("📑API文档", "📑API Document")):
        put_markdown(t("> 介绍",
                       "> Introduction"))
        put_markdown(t("你可以利用本项目提供的API接口来获取抖音/TikTok的数据，具体接口文档请参考下方链接。",
                       "You can use the API provided by this project to obtain Douyin/TikTok data. For specific API documentation, please refer to the link below."))
        put_markdown(t("如果API不可用，请尝试自己部署本项目，然后再配置文件中修改cookie的值。",
                       "If the API is not available, please try to deploy this project by yourself, and then modify the value of the cookie in the configuration file."))
        put_link('[API Docs]', '/docs', new_window=True)
        put_markdown("----")
        put_markdown(t("> 更多接口",
                       "> More APIs"))
        put_markdown(
            t("[TikHub.io](https://beta-web.tikhub.io/en-us/users/signin)是一个API平台，提供包括Douyin、TikTok在内的各种公开数据接口，如果您想支持 [Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API) 项目的开发，我们强烈建议您选择[TikHub.io](https://beta-web.tikhub.io/en-us/users/signin)。",
              "[TikHub.io](https://beta-web.tikhub.io/en-us/users/signin) is an API platform that provides various public data interfaces including Douyin and TikTok. If you want to support the development of the [Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API) project, we strongly recommend that you choose [TikHub.io](https://beta-web.tikhub.io/en-us/users/signin)."))
        put_markdown(
            t("#### 特点：",
              "#### Features:"))
        put_markdown(
            t("> 📦 开箱即用",
              "> 📦 Ready to use"))
        put_markdown(
            t("简化使用流程，利用封装好的SDK迅速开展开发工作。所有API接口均依据RESTful架构设计，并使用OpenAPI规范进行描述和文档化，附带示例参数，确保调用更加简便。",
                "Simplify the use process and quickly carry out development work using the encapsulated SDK. All API interfaces are designed based on the RESTful architecture and described and documented using the OpenAPI specification, with example parameters attached to ensure easier calls."))
        put_markdown(
            t("> 💰 成本优势",
              "> 💰 Cost advantage"))
        put_markdown(
            t("不预设套餐限制，没有月度使用门槛，所有消费按实际使用量即时计费，并且根据用户每日的请求量进行阶梯式计费，同时可以通过每日签到在用户后台进行签到获取免费的额度，并且这些免费额度不会过期。",
              "There is no preset package limit, no monthly usage threshold, all consumption is billed in real time according to the actual usage, and billed in a step-by-step manner according to the user's daily request volume. At the same time, you can sign in daily in the user background to get free quotas, and these free quotas will not expire."))
        put_markdown(
            t("> ⚡️ 快速支持",
              "> ⚡️ Quick support"))
        put_markdown(
            t("我们有一个庞大的Discord社区服务器，管理员和其他用户会在服务器中快速的回复你，帮助你快速解决当前的问题。",
              "We have a huge Discord community server, where administrators and other users will quickly reply to you in the server and help you quickly solve the current problem."))
        put_markdown(
            t("> 🎉 拥抱开源",
              "> 🎉 Embrace open source"))
        put_markdown(
            t("TikHub的部分源代码会开源在Github上，并且会赞助一些开源项目的作者。",
              "Some of TikHub's source code will be open sourced on Github, and will sponsor some open source project authors."))
        put_markdown(
            t("#### 链接：",
              "#### Links:"))
        put_markdown(
            t("- Github: [TikHub Github](https://github.com/TikHubIO)",
                "- Github: [TikHub Github](https://github.com/TikHubIO)"))
        put_markdown(
            t("- Discord: [TikHub Discord](https://discord.com/invite/aMEAS8Xsvz)",
              "- Discord: [TikHub Discord](https://discord.com/invite/aMEAS8Xsvz)"))
        put_markdown(
            t("- Register: [TikHub signup](https://beta-web.tikhub.io/en-us/users/signup)",
              "- Register: [TikHub signup](https://beta-web.tikhub.io/en-us/users/signup)"))
        put_markdown(
            t("- API Docs: [TikHub API Docs](https://api.tikhub.io/)",
              "- API Docs: [TikHub API Docs](https://api.tikhub.io/)"))
        put_markdown("----")
