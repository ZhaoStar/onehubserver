from pywebio.output import popup, put_markdown, put_html, put_text, put_link
from app.douyin_api.web.views.ViewsUtils import ViewsUtils

t = ViewsUtils().t


# 下载器弹窗/Downloader pop-up
def downloader_pop_window():
    with popup(t("💾 下载器", "💾 Downloader")):
        put_markdown(t("> 桌面端下载器", "> Desktop Downloader"))
        put_markdown(t("你可以使用下面的开源项目在桌面端下载视频：",
                       "You can use the following open source projects to download videos on the desktop:"))
        put_markdown("1. [TikTokDownload](https://github.com/Johnserf-Seed/TikTokDownload)")
        put_markdown(t("> 备注", "> Note"))
        put_markdown(t("1. 请注意下载器的使用规范，不要用于违法用途。",
                       "1. Please pay attention to the use specifications of the downloader and do not use it for illegal purposes."))
        put_markdown(t("2. 下载器相关问题请咨询对应项目的开发者。",
                       "2. For issues related to the downloader, please consult the developer of the corresponding project."))
