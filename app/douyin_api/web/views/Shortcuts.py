import os
import yaml
from pywebio.output import popup, put_markdown, put_html, put_text, put_link
from app.douyin_api.web.views.ViewsUtils import ViewsUtils

t = ViewsUtils().t

# 读取上级再上级目录的配置文件
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)
    config = config['iOS_Shortcut']


# iOS快捷指令弹窗/IOS shortcut pop-up
def ios_pop_window():
    with popup(t("iOS快捷指令", "iOS Shortcut")):
        version = config["iOS_Shortcut_Version"]
        update = config['iOS_Shortcut_Update_Time']
        link = config['iOS_Shortcut_Link']
        link_en = config['iOS_Shortcut_Link_EN']
        note = config['iOS_Shortcut_Update_Note']
        note_en = config['iOS_Shortcut_Update_Note_EN']
        put_markdown(t('#### 📢 快捷指令介绍:', '#### 📢 Shortcut Introduction:'))
        put_markdown(
            t('快捷指令运行在iOS平台，本快捷指令可以快速调用本项目的公共API将抖音或TikTok的视频或图集下载到你的手机相册中，暂时只支持单个链接进行下载。',
              'The shortcut runs on the iOS platform, and this shortcut can quickly call the public API of this project to download the video or album of Douyin or TikTok to your phone album. It only supports single link download for now.'))
        put_markdown(t('#### 📲 使用方法 ①:', '#### 📲 Operation method ①:'))
        put_markdown(t('在抖音或TikTok的APP内，浏览你想要无水印保存的视频或图集。',
                       'The shortcut needs to be used in the Douyin or TikTok app, browse the video or album you want to save without watermark.'))
        put_markdown(t('然后点击右下角分享按钮，选择更多，然后下拉找到 "抖音TikTok无水印下载" 这个选项。',
                       'Then click the share button in the lower right corner, select more, and then scroll down to find the "Douyin TikTok No Watermark Download" option.'))
        put_markdown(t('如遇到通知询问是否允许快捷指令访问xxxx (域名或服务器)，需要点击允许才可以正常使用。',
                       'If you are asked whether to allow the shortcut to access xxxx (domain name or server), you need to click Allow to use it normally.'))
        put_markdown(t('该快捷指令会在你相册创建一个新的相薄方便你浏览保存的内容。',
                       'The shortcut will create a new album in your photo album to help you browse the saved content.'))
        put_markdown(t('#### 📲 使用方法 ②:', '#### 📲 Operation method ②:'))
        put_markdown(t('在抖音或TikTok的视频下方点击分享，然后点击复制链接，然后去快捷指令APP中运行该快捷指令。',
                       'Click share below the video of Douyin or TikTok, then click to copy the link, then go to the shortcut command APP to run the shortcut command.'))
        put_markdown(t('如果弹窗询问是否允许读取剪切板请同意，随后快捷指令将链接内容保存至相册中。',
                       'if the pop-up window asks whether to allow reading the clipboard, please agree, and then the shortcut command will save the link content to the album middle.'))
        put_html('<hr>')
        put_text(t(f"最新快捷指令版本: {version}", f"Latest shortcut version: {version}"))
        put_text(t(f"快捷指令更新时间: {update}", f"Shortcut update time: {update}"))
        put_text(t(f"快捷指令更新内容: {note}", f"Shortcut update content: {note_en}"))
        put_link("[点击获取快捷指令 - 中文]", link, new_window=True)
        put_html("<br>")
        put_link("[Click get Shortcut - English]", link_en, new_window=True)
