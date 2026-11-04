import {chinaTime} from "./schedule.mjs";
const date=document.getElementById("date");date.value=chinaTime().date;
date.onchange=()=>window.dispatchEvent(new CustomEvent("schedule-date-change",{detail:date.value}));
