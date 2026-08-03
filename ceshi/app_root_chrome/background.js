chrome.browserAction.onClicked.addListener(function(tab) {
    // 向当前活动的页面发送消息，指示其注入 UI
    chrome.tabs.sendMessage(tab.id, { action: "TOGGLE_UI" });
});
