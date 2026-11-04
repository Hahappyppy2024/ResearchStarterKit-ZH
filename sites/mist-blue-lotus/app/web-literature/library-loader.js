import('./library.js').catch(error=>{const status=document.getElementById('conference-total');if(status)status.textContent='会议页面加载失败：'+error.message;});
