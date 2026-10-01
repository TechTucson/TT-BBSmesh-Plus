const $ = id => document.getElementById(id);
function formatFreq(hz){ return (hz/1e6).toFixed(6).replace(/(\d\.\d{3})(\d{3})/,'$1.$2')+' MHz'; }
function update(d){
  $('status').textContent=d.running?'RECEIVING':'STOPPED';
  $('status').className='pill '+(d.running?'ok':'bad');
  $('freq').textContent=formatFreq(d.frequency||7050000);
  $('level').textContent=(d.level??0).toFixed(1);
  $('tone').textContent=(d.tone_hz||700)+' Hz';
  $('wpm').textContent=(d.wpm||18)+' WPM';
  $('key').textContent=d.keyed?'ON':'OFF';
  $('decoded').textContent=d.text||'Waiting for CW…';
  $('raw').textContent=(d.raw||'')+(d.pending||'');
  $('error').textContent=d.error||'';
  const level=Math.min(100,Math.max(0,(d.level||0)/4));
  $('meter').style.width=level+'%';
}
function connect(){
  const proto=location.protocol==='https:'?'wss':'ws';
  const ws=new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage=e=>update(JSON.parse(e.data));
  ws.onclose=()=>setTimeout(connect,1500);
}
$('tune').addEventListener('submit',async e=>{
  e.preventDefault();
  const frequency=parseInt($('frequency').value,10);
  const r=await fetch('/api/tune',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frequency})});
  const d=await r.json(); if(!d.ok) $('error').textContent=d.error;
});
connect();
