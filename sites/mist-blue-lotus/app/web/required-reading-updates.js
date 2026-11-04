// storage events reach other same-origin tabs/iframes; the custom event reaches this one.
export function notifyRequiredReading(){
 try{localStorage.setItem('required-reading-updated',Date.now()+':'+crypto.randomUUID())}catch{}
 window.dispatchEvent(new Event('required-reading-change'));
}
