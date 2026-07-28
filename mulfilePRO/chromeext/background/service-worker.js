chrome.action.onClicked.addListener((tab) => {
  console.log("【排查日志】捕获到图标点击事件！Tab ID:", tab.id);
  
  if (!tab.id) return;
  
  // 1. 强行注入 CSS 样式
  chrome.scripting.insertCSS({
    target: { tabId: tab.id },
    files: ["content/content-style.css"]
  }, () => {
    if (chrome.runtime.lastError) {
      console.log("【排查日志】CSS 注入失败:", chrome.runtime.lastError.message);
    } else {
      console.log("【排查日志】CSS 样式注入成功");
    }
  });

  // 2. 注入 JavaScript 逻辑
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content/content-script.js"]
  }, () => {
    if (chrome.runtime.lastError) {
      console.log("【排查日志】JS 注入失败:", chrome.runtime.lastError.message);
    } else {
      console.log("【排查日志】JS 逻辑注入成功");
    }
  });
});