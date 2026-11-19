"""Demo-only UI and rehearsal routes (disable via ENABLE_DEMO_ROUTES=0 in production)."""
import uuid

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

import config
from store import (
    clear_demo_store,
    hit_breakpoint,
    link_tokens,
    now_iso,
    received,
    sent_requests,
)
from webhook_reader import poll_webhook_site, wait_for_callback

router = APIRouter()


@router.get("/callbacks", tags=["Demo"])
async def list_callbacks():
    return {"sent": sent_requests, "received": received, "link_tokens": link_tokens}


@router.get("/m1-status", tags=["Demo"])
async def m1_status():
    from store import m1_linked_patients, m1_patient_tokens, m1_verifications, m1_otp_txns
    return {
        "otp_transactions": m1_otp_txns,
        "active_verifications": m1_verifications,
        "linked_patients": m1_linked_patients,
        "verified_patients": list(m1_patient_tokens.keys()),
    }


@router.get("/link-token/{abha_address}", tags=["Demo"])
async def get_saved_link_token(abha_address: str):
    """Look up the extracted linkToken saved by Python from the webhook callback."""
    key = abha_address.strip().lower()
    if key not in link_tokens:
        raise HTTPException(404, "No link token received yet for this ABHA address")
    return link_tokens[key]


@router.post("/poll-now", tags=["Demo"])
async def poll_now():
    return {"new_callbacks": await poll_webhook_site()}


@router.post("/simulate", tags=["Demo"])
async def simulate():
    """Safe rehearsal (no ABDM quota used): sends fake on-generate-token callback to webhook.site."""
    if not config.WEBHOOK_SITE_URL:
        raise HTTPException(400, "WEBHOOK_SITE_TOKEN is required for /simulate")

    rid = str(uuid.uuid4())
    demo_abha = "demo.user@sbx"
    sent_requests[rid] = {
        "label": "simulated generate-token",
        "method": "POST",
        "url": config.GENERATE_TOKEN_URL,
        "payload": {"abhaAddress": demo_abha, "name": "Demo User", "yearOfBirth": 1998, "gender": "M"},
        "sent_at": now_iso(),
        "http_status": 202,
    }
    hit_breakpoint("2", "Simulated sending generate-token to ABDM", request_id=rid)
    hit_breakpoint("3", "Simulated immediate HTTP 202 Accepted", request_id=rid)

    fake_callback = {
        "abhaAddress": demo_abha,
        "linkToken": "DEMO." + uuid.uuid4().hex * 2,
        "response": {"requestId": rid},
    }
    async with httpx.AsyncClient(timeout=config.POLL_TIMEOUT) as client:
        await client.post(f"{config.WEBHOOK_SITE_URL}/api/v3/hip/token/on-generate-token", json=fake_callback)

    cb = await wait_for_callback(rid, timeout_sec=config.SIMULATE_WAIT_SECONDS)
    return {
        "simulated_request_id": rid,
        "callback_read": bool(cb),
        "saved_link_token": link_tokens.get(demo_abha),
    }


@router.post("/reset-demo", tags=["Demo"])
async def reset_demo():
    clear_demo_store()
    return {"reset": True}


@router.get("/bridge-url", tags=["Demo"])
async def get_bridge_url():
    """Returns configured webhook bridge URL for quick copying."""
    return {
        "bridge_url": config.WEBHOOK_SITE_URL,
        "webhook_token": config.WEBHOOK_SITE_TOKEN,
        "bridge_endpoint": config.BRIDGE_URL_ENDPOINT,
    }


@router.get("/dashboard", response_class=HTMLResponse, tags=["Demo"])
async def dashboard():
    bridge_url = config.WEBHOOK_SITE_URL
    html = """<!doctype html><html><head><meta charset="utf-8">
<title>ABDM M2: Generate Link Token</title>
<style>
 *{box-sizing:border-box}
 body{font-family:system-ui,Segoe UI,sans-serif;margin:22px;background:#f4f6f9;color:#1e293b}
 h1{margin:0 0 4px} .sub{color:#64748b;font-size:13px;margin-bottom:14px}
 .flow{display:flex;align-items:center;flex-wrap:wrap;gap:6px;background:#fff;border:1px solid #cbd5e1;border-radius:10px;padding:12px;margin-bottom:14px;font-size:13px}
 .box{background:#eff6ff;border:1px solid #93c5fd;border-radius:6px;padding:6px 10px}
 .ar{color:#94a3b8;font-weight:700}
 .panel{background:#fff;border:1px solid #cbd5e1;border-radius:10px;padding:14px;margin-bottom:14px}
 .form-row{display:flex;flex-wrap:wrap;gap:8px;align-items:end;margin-bottom:10px}
 label{font-size:11px;font-weight:700;color:#475569;display:flex;flex-direction:column;gap:3px}
 input,select{padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;min-width:130px}
 .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
 .btn{background:#1d4ed8;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
 .btn.green{background:#15803d} .btn.gray{background:#475569} .btn.copy{background:#0891b2}
 .btn:disabled{opacity:.5;cursor:wait}
 .cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
 @media(max-width:900px){.cols{grid-template-columns:1fr}}
 .card{background:#fff;border:1px solid #cbd5e1;border-radius:8px;padding:10px;margin-bottom:10px}
 .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;background:#dbeafe;color:#1e40af}
 .ok{background:#dcfce7;color:#166534} .err{background:#fee2e2;color:#991b1b} .tok{background:#fffbeb;border-color:#f59e0b}
 pre{background:#0f172a;color:#e2e8f0;padding:8px;border-radius:6px;overflow:auto;font-size:11px;white-space:pre-wrap;word-break:break-all;margin:6px 0 0}
 small{color:#64748b}
 .bridge-box{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:#f8fafc;border:1px solid #e2e8f0;padding:10px;border-radius:8px;margin-bottom:12px}
</style></head><body>
<h1>ABDM M2: Generate Link Token</h1>
<p class="sub">Auto-refreshes every 2s &nbsp;|&nbsp; <a href="/docs" target="_blank">Swagger /docs</a> &nbsp;|&nbsp; <a href="/callbacks" target="_blank">Raw JSON</a></p>

<div class="flow">
  <div class="box">1. Postman sends Link Token API<br><small>ABDM replies HTTP 202</small></div><span class="ar">--&gt;</span>
  <div class="box">2. ABDM posts callback to webhook.site<br><small>Contains linkToken + requestId</small></div><span class="ar">--&gt;</span>
  <div class="box">3. Python polls &amp; parses webhook<br><small>Matches REQUEST-ID &amp; extracts linkToken</small></div><span class="ar">--&gt;</span>
  <div class="box">4. Shown live below<br><small>Yellow card + full JSON</small></div>
</div>

<div class="bar" style="margin-bottom:14px">
  <button class="btn green" onclick="callApi('/register-bridge',this)">Register Bridge URL</button>
  <button class="btn copy" onclick="copyBridgeUrl(this)">📋 Copy Bridge URL</button>
  <button class="btn gray" onclick="callApi('/poll-now',this)">Poll Now</button>
  <button class="btn gray" onclick="callApi('/reset-demo',this)">Clear View</button>
</div>
<div id="msg" style="display:none;margin-bottom:14px;padding:8px 10px;border-radius:6px;font-size:12px"></div>

<div id="tok"></div>

<div class="cols">
 <div><h2>1. Requests sent to ABDM</h2><div id="sent"></div></div>
 <div><h2>2. Webhook responses read by Python</h2><div id="recv"></div></div>
</div>

<script>
const BRIDGE_URL = "__BRIDGE_URL__";
const esc=s=>String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function fallbackCopy(text){
  const ta=document.createElement('textarea');
  ta.value=text;
  ta.style.position='fixed';
  ta.style.left='-9999px';
  document.body.appendChild(ta);
  ta.select();
  try{ document.execCommand('copy'); }catch(e){}
  document.body.removeChild(ta);
}

function copyBridgeUrl(btn){
  const orig = btn.innerHTML;
  const done=()=>{
    btn.innerHTML='✅ Copied!';
    const oldBg=btn.style.background;
    btn.style.background='#15803d';
    setTimeout(()=>{ btn.innerHTML=orig; btn.style.background=oldBg; }, 2000);
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(BRIDGE_URL).then(done).catch(()=>{ fallbackCopy(BRIDGE_URL); done(); });
  }else{
    fallbackCopy(BRIDGE_URL);
    done();
  }
}
function copyTextVal(btn, val){
  const orig = btn.innerHTML;
  const done=()=>{
    btn.innerHTML='✅ Copied!';
    const oldBg=btn.style.background;
    btn.style.background='#15803d';
    setTimeout(()=>{ btn.innerHTML=orig; btn.style.background=oldBg; }, 2000);
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(val).then(done).catch(()=>{ fallbackCopy(val); done(); });
  }else{
    fallbackCopy(val);
    done();
  }
}
function showMsg(ok,text){
  const m=document.getElementById('msg');
  m.style.display='block';
  m.style.background=ok?'#dcfce7':'#fee2e2';
  m.textContent=text;
}
async function callApi(url,btn,bodyObj=null){
  const t=btn.textContent; btn.disabled=true; btn.textContent='Working...';
  try{
    const opts={method:'POST'};
    if(bodyObj){opts.headers={'Content-Type':'application/json'}; opts.body=JSON.stringify(bodyObj);}
    const r=await fetch(url,opts);
    const d=await r.json();
    showMsg(r.ok, url+' -> HTTP '+r.status+' | '+JSON.stringify(d).slice(0,220));
    await load();
  }catch(e){ showMsg(false,'Error: '+e); }
  finally{ btn.disabled=false; btn.textContent=t; }
}
async function load(){
  const d=await (await fetch('/callbacks')).json();
  document.getElementById('tok').innerHTML=Object.entries(d.link_tokens||{}).map(([a,t])=>
   `<div class="card tok">
    <button class="btn copy" style="float:right;padding:3px 8px;font-size:11px" onclick="copyTextVal(this, esc('${esc(t.linkToken)}'))">📋 Copy Token</button>
    <b>Link token received for ${esc(a)}</b><br>
    <small>request_id: ${esc(t.request_id)} | ${esc(t.received_at)}</small>
    <pre>${esc(t.linkToken)}</pre></div>`).join('');

  document.getElementById('sent').innerHTML=Object.entries(d.sent||{}).reverse().map(([id,r])=>{
    const ok=r.http_status>=200&&r.http_status<300;
    const isBridge = r.label==='register-bridge' || (r.payload && r.payload.url);
    return `<div class="card">
      ${isBridge ? `<button class="btn copy" style="float:right;padding:3px 8px;font-size:11px" onclick="copyBridgeUrl(this)">📋 Copy Bridge URL</button>` : ''}
      <b>${esc(r.label)}</b> <span class="badge ${ok?'ok':'err'}">HTTP ${esc(r.http_status??'...')}</span><br>
      <small>${esc(r.method)} ${esc(r.url)}<br>request_id: ${esc(id)}<br>${esc(r.sent_at)}</small>
      ${r.payload?`<pre>${esc(JSON.stringify(r.payload,null,2))}</pre>`:''}
      ${r.immediate_response?`<pre>${esc(r.immediate_response)}</pre>`:''}</div>`;
  }).join('')||'<small>none yet</small>';

  document.getElementById('recv').innerHTML=(d.received||[]).slice().reverse().map(c=>
   `<div class="card"><b>${esc(c.method||'')} ${esc(c.path)}</b>
    <span class="badge ok">matched: ${esc(c.matched_request??'no match')}</span>
    ${c.has_link_token?'<span class="badge ok">linkToken</span>':''}
    ${(c.payload&&c.payload.status)?'<span class="badge ok">'+esc(c.payload.status)+'</span>':''}
    ${c.payload&&c.payload.error?'<span class="badge err">error</span>':''}<br>
    <small>${esc(c.received_at)} | request_id: ${esc(c.request_id??'-')}</small>
    <pre>${esc(JSON.stringify(c.payload,null,2))}</pre></div>`).join('')||'<small>waiting for ABDM callback...</small>';
}
load();setInterval(load,1000);
</script></body></html>"""
    return html.replace("__BRIDGE_URL__", bridge_url)

