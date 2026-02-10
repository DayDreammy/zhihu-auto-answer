#!/usr/bin/env python3
"""
知乎选择器配置 - 根据实际情况调整
知乎页面经常更新，这里提供多种备选选择器
"""

# 通知列表相关
NOTIFICATION_SELECTORS = [
    # 新版知乎
    '.NotificationList-item',
    '[class*="NotificationList"] > div',
    '[data-za-detail-view-element_name="通知列表"] > div',
    # 通用
    '.List-item',
    '.ContentItem',
    # 兜底
    'div[role="listitem"]',
]

# 邀请回答的文本特征
INVITATION_KEYWORDS = [
    '邀请你回答',
    '邀请回答',
    '向你提问',
    '邀请你',
]

# 问题链接选择器
QUESTION_LINK_SELECTORS = [
    'a[href*="/question/"]',
    'a[href*="zhihu.com/question"]',
]

# 登录状态检查
LOGIN_INDICATORS = [
    '.AppHeader-profileEntryAvatar',
    '[data-za-detail-view-element_name="个人头像"]',
    'img[alt*="头像"]',
    '.AppHeader-userInfo',
]

# 写回答按钮
WRITE_ANSWER_BUTTONS = [
    'button:has-text("写回答")',
    'button:has-text("添加回答")',
    '[data-za-detail-view-element_name="写回答"]',
    'a[href*="/write"]',
    'button[class*="Answer"]',
]

# 编辑器选择器
EDITOR_SELECTORS = [
    '.RichText-editable',
    '[contenteditable="true"]',
    '.DraftEditor-root',
    '[data-editor]',
    'div[role="textbox"]',
    '.public-DraftEditor-content',
    'textarea[placeholder*="回答"]',
]

# 保存草稿按钮
SAVE_DRAFT_BUTTONS = [
    'button:has-text("保存草稿")',
    'button:has-text("存草稿")',
    'button:has-text("草稿")',
]

# 问题标题
QUESTION_TITLE_SELECTORS = [
    'h1.QuestionHeader-title',
    '[class*="QuestionHeader-title"]',
    'h1[data-za-detail-view-element_name="问题标题"]',
]

# 问题描述
QUESTION_CONTENT_SELECTORS = [
    '.QuestionRichText',
    '[class*="QuestionRichText"]',
    '.RichContent-inner',
    '[data-za-detail-view-element_name="问题描述"]',
    '.QuestionRichText-content',
]
