const only=new URLSearchParams(location.search).get('quizOnly')==='1';
document.body.classList.add(only?'quiz-only':'foundations-study');
if(only){document.querySelector('#daily-interviews h2').textContent='基础知识 · 每日 Quiz';document.querySelector('#daily-interviews .eyebrow').textContent='DAILY QUIZ';document.getElementById('daily-date').closest('.actions').hidden=true;}
else{document.getElementById('daily-interviews').hidden=true;}

if(!only&&['evening','quiz'].includes(new URLSearchParams(location.search).get('practice')))location.replace('http://127.0.0.1:8866/daily-quiz.html?section=foundation');
