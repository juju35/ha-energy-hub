// ── Styles and registration ──────────────────────────────────────────────────
import { ENERGY_HUB_PANEL_VERSION } from "./core.js";
import { EH_AMBER, EH_RED, EH_TEAL, EH_VIOLET } from "./colours-helpers.js";
import { EnergyHubPanel } from "./panel.js";

export const EH_CSS = `
:host{display:block;height:100%;background:var(--primary-background-color);color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
.scroll{height:100%;overflow-y:auto;overflow-x:hidden}
.ic{flex-shrink:0;display:block}
.banner{position:sticky;top:0;z-index:3;height:90px;overflow:hidden;transition:height .2s;background:var(--sky)}
.banner::before{content:'';position:absolute;left:0;right:0;bottom:0;height:6px;background:var(--ground)}
.banner .scene{position:absolute;inset:0;width:100%;height:100%}
.banner .bar{position:relative;display:flex;align-items:center;gap:12px;height:90px;padding:0 14px;transition:height .2s}
.banner .badge{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.banner .titles{min-width:0}
.banner .title{font-size:18px;font-weight:500;color:var(--txt);display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.banner .sub{font-size:12px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pill{font-size:11px;font-weight:400;padding:2px 8px;border-radius:10px;white-space:nowrap}
.pill.demo{background:#EEEDFE;color:#3C3489}
.pill.small{background:var(--secondary-background-color);color:var(--secondary-text-color);font-size:10px;padding:1px 6px}
.round{width:32px;height:32px;border-radius:50%;border:0;background:var(--btn);color:var(--txt);display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;margin-left:auto}
.round.menu{display:none;margin-left:0}
.narrow .round.menu{display:flex}
.tabpills{display:none;gap:4px;margin-left:auto}
.tabpill{width:30px;height:30px;border-radius:50%;border:0;background:var(--btn);color:var(--sub);display:flex;align-items:center;justify-content:center;cursor:pointer;position:relative}
.tabpill.on{background:#FAC775;color:#633806}
.dot{position:absolute;top:2px;right:2px;width:7px;height:7px;border-radius:4px;background:${EH_RED}}
.dot.inline{position:static;display:inline-block;margin-left:4px;vertical-align:6px}
.banner.collapsed{height:52px;box-shadow:0 1px 0 var(--divider-color)}
.banner.collapsed .scene{opacity:0}
.banner.collapsed .bar{height:52px}
.banner.collapsed .badge{width:32px;height:32px}
.banner.collapsed .sub{display:none}
.banner.collapsed .title{font-size:14px}
.banner.collapsed .tabpills{display:flex}
.banner.collapsed .round:not(.menu){margin-left:0}
.banner.collapsed::before{height:3px}
.tabs{display:flex;gap:18px;padding:0 16px;border-bottom:1px solid var(--divider-color);background:var(--card-background-color);overflow-x:auto}
.tab{border:0;background:none;padding:11px 0;font:inherit;font-size:14px;color:var(--secondary-text-color);cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent}
.tab.on{color:var(--primary-text-color);font-weight:500;border-bottom-color:${EH_AMBER}}
main{padding:12px 16px 32px;max-width:1100px;margin:0 auto;display:flex;flex-direction:column;gap:12px}
.flow{width:100%;max-width:760px;margin:0 auto;display:block}
.node{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:14px;padding:8px 10px;display:flex;gap:9px;align-items:center;height:100%;box-sizing:border-box}
.pa{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.pa.sm{width:24px;height:24px}
.tt{min-width:0;flex:1}
.t1{font-size:11px;color:var(--secondary-text-color);line-height:1.25}
.t2{font-size:16px;font-weight:500;line-height:1.3}
.t3{font-size:11px;line-height:1.25;color:var(--secondary-text-color)}
.soc{height:4px;border-radius:2px;background:var(--divider-color);margin-top:4px}
.soc div{height:4px;border-radius:2px;background:${EH_TEAL}}
.svgt{font-size:12px;fill:var(--secondary-text-color)}
.svgth{font-size:14px;font-weight:500;fill:var(--primary-text-color)}
.svgt.dark,.svgth.dark{fill:#412402}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.kpi{background:var(--secondary-background-color);border-radius:10px;padding:9px 11px}
.k1{font-size:12px;color:var(--secondary-text-color)}
.k2{font-size:19px;font-weight:500}
.k3{font-size:11px;color:var(--secondary-text-color)}
.box{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:12px;padding:10px 12px}
.hd{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.box h3{margin:0;font-size:14px;font-weight:500}
.hint{font-size:11px;color:var(--secondary-text-color)}
.legend{display:flex;flex-wrap:wrap;gap:6px 12px;margin:2px 0 6px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--secondary-text-color)}
.sw{width:10px;height:10px;border-radius:3px;display:inline-block}
.curvewrap{position:relative}
.curve{width:100%;display:block}
.curve .svgt{font-size:9px}
.tip{position:absolute;top:8px;pointer-events:none;background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:8px;padding:6px 9px;font-size:12px;line-height:1.5;min-width:130px;display:none;box-shadow:0 2px 8px rgba(0,0,0,.12)}
.tip b{font-weight:500}
.grid-auto{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}
.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}
.grid2.tight{gap:8px}
.tile{background:var(--secondary-background-color);border-radius:12px;padding:9px 10px;display:flex;gap:9px;align-items:center;min-width:0}
.tile.col{flex-direction:column;justify-content:center;text-align:center}
.alert,.bcard{background:var(--secondary-background-color);border:0;border-radius:12px;padding:10px 12px;display:flex;gap:10px;align-items:center;cursor:pointer;font:inherit;color:inherit;text-align:left;width:100%}
.bcard{background:var(--card-background-color);border:1px solid var(--divider-color)}
.bcard.on{border:2px solid ${EH_TEAL};padding:9px 11px}
.a1{font-size:13px;font-weight:500}
.a2{font-size:12px}
.muted{color:var(--secondary-text-color);font-weight:400}
.brand{display:inline-block;font-size:10px;padding:1px 6px;border-radius:8px;background:var(--secondary-background-color);color:var(--secondary-text-color);margin-top:3px}
.roof{width:100%;max-width:640px;margin:0 auto;display:block}
.mini{width:100%;display:block}
.mini .svgt{font-size:8px}
.mini.m .svgt{font-size:11px}
.barrow{display:grid;grid-template-columns:110px minmax(0,1fr) 120px;gap:8px;align-items:center;font-size:12px;margin:6px 0}
.barrow span:last-child{text-align:right}
.meter{height:10px;border-radius:5px;background:var(--secondary-background-color);overflow:hidden}
.meter div{height:10px}
.stack{display:flex;height:22px;border-radius:6px;overflow:hidden;font-size:11px;color:#fff}
.stack div{display:flex;align-items:center;padding-left:6px;white-space:nowrap;overflow:hidden}
.stack.thin{height:14px}
.seg{display:inline-flex;background:var(--secondary-background-color);border-radius:8px;padding:2px}
.seg button{font:inherit;font-size:12px;padding:3px 10px;border-radius:6px;color:var(--secondary-text-color);background:none;border:0;cursor:pointer}
.seg button.on{background:var(--card-background-color);color:var(--primary-text-color)}
.cells{display:grid;gap:3px;margin:4px 0 8px}
.cell{height:34px;border-radius:5px;border:0;font:inherit;font-size:10px;color:var(--primary-text-color);cursor:pointer;padding:0}
.cell.sel{outline:2px solid var(--primary-text-color);outline-offset:1px}
.ringrow{display:grid;grid-template-columns:150px minmax(0,1fr);gap:12px;align-items:center}
.slider{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--secondary-text-color);margin-bottom:6px}
.slider b{font-weight:500;color:var(--primary-text-color)}
.check{display:flex;gap:9px;align-items:center;padding:6px 0;border-top:1px solid var(--divider-color)}
.check:first-child{border-top:0}
.src{padding:8px 0;border-top:1px solid var(--divider-color)}
.src:first-of-type{border-top:0}
.cap{display:inline-flex;align-items:center;gap:3px;font-size:11px;padding:1px 7px;border-radius:8px;margin:3px 4px 0 0}
.cap.provided{background:#EAF3DE;color:#27500A}
.cap.estimated{background:#FAEEDA;color:#633806}
.cap.absent{background:var(--secondary-background-color);color:var(--secondary-text-color)}
.roles{width:100%;border-collapse:collapse;font-size:12px}
.offers{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}
.offers td{padding:6px 4px;border-top:1px solid var(--divider-color);vertical-align:top}
.offers tr.th td{border-top:0;color:var(--secondary-text-color);font-size:11px}
.offers tr.cur td{background:var(--secondary-background-color)}
.offers .oname{display:flex;align-items:center;gap:4px}
.offers td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.pill.small.cur{background:#E6F1FB;color:#185FA5}
.verdict{font-size:13px;padding:8px 10px;border-radius:8px;background:var(--secondary-background-color)}
.verdict.gain{background:#EAF3DE;color:#27500A}
.roles td{padding:5px 4px;border-top:1px solid var(--divider-color);vertical-align:top}
.roles td.age{text-align:right;color:var(--secondary-text-color);white-space:nowrap}
code,pre{font-family:var(--code-font-family,ui-monospace,monospace)}
pre{background:var(--secondary-background-color);border-radius:8px;padding:10px 12px;font-size:12px;overflow-x:auto;margin:6px 0 0}
.copy{font:inherit;font-size:12px;border:1px solid var(--divider-color);background:var(--card-background-color);color:var(--primary-text-color);border-radius:8px;padding:3px 10px;cursor:pointer;display:inline-flex;align-items:center;gap:4px}
.empty{padding:40px 16px;text-align:center;color:var(--secondary-text-color)}
.pill .short{display:none}
.banner.collapsed .pill .long{display:none}
.banner.collapsed .pill .short{display:inline}
.banner.collapsed .pill.demo{display:none}
.bell{position:relative}
.bell .count{position:absolute;top:-3px;right:-3px;min-width:16px;height:16px;border-radius:8px;background:${EH_RED};color:#fff;font-size:10px;font-weight:500;display:flex;align-items:center;justify-content:center;padding:0 4px;box-sizing:border-box}
.round.bell{margin-left:auto}
.round.refresh{margin-left:0}
.banner.collapsed .round.bell{margin-left:0}
.refresh-inline{display:none;margin-left:auto;--btn:var(--secondary-background-color)}
.hd.sub{margin-bottom:4px}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.battrow{display:grid;grid-template-columns:150px minmax(0,1fr);gap:14px;align-items:center}
.bbwrap{display:flex;flex-direction:column;align-items:center;gap:2px;text-align:center}
.bigbatt{width:110px;height:auto}
.cellrow{display:grid;grid-template-columns:70px minmax(0,1fr);gap:8px;align-items:center}
.cellrow .cells{margin:2px 0}
.rowlab{font-size:11px;color:var(--secondary-text-color)}
.cell{position:relative}
.cell.drift{outline:2px solid ${EH_RED};outline-offset:-2px}
.baldot{position:absolute;top:3px;right:3px;width:6px;height:6px;border-radius:3px;background:${EH_VIOLET}}
.baldot.static{position:static;display:inline-block}
.diag{align-self:start;display:flex;gap:8px;align-items:flex-start;font-size:12px;background:#EAF3DE;color:#27500A;border-radius:10px;padding:10px}
.diag.bad{background:#FCEBEB;color:#791F1F}
.event{display:flex;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--divider-color)}
.event:first-child{border-top:0}
.status{font-size:11px;padding:2px 9px;border-radius:10px;white-space:nowrap}
.calgrid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:3px}
.calh{font-size:10px;color:var(--secondary-text-color);text-align:center}
.cal{border-radius:6px;min-height:34px;padding:3px 4px;display:flex;flex-direction:column;justify-content:space-between;font-size:10px}
.cal b{font-weight:500;font-size:11px;text-align:right}
.cal.today{outline:2px solid var(--primary-text-color);outline-offset:-2px}
.calscale{flex:1;max-width:160px;height:8px;border-radius:4px;background:linear-gradient(90deg,rgba(99,153,34,.12),rgba(99,153,34,.92))}
.billrow{padding:6px 0;border-top:1px solid var(--divider-color)}
.billrow:first-child{border-top:0}
.subtabs{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.subtabs button:not(.round){font:inherit;font-size:13px;padding:5px 12px;border-radius:16px;border:1px solid var(--divider-color);background:var(--card-background-color);color:var(--secondary-text-color);cursor:pointer}
.subtabs button.on{background:#FAC775;border-color:#FAC775;color:#633806}
.sugg{display:flex;gap:9px;align-items:center;padding:6px 0;border-top:1px solid var(--divider-color)}
.sugg:first-child{border-top:0}
.rolehead{font-size:11px;font-weight:500;color:var(--secondary-text-color);text-transform:uppercase;letter-spacing:.04em;margin:10px 0 2px}
.rolehead:first-child{margin-top:0}
.qrow{display:grid;grid-template-columns:200px minmax(0,1fr) 110px;gap:10px;align-items:center;padding:5px 0;border-top:1px solid var(--divider-color)}
.qrow:first-child{border-top:0}
.qname code{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.qbar{display:grid;grid-template-columns:repeat(96,1fr);gap:1px;height:14px}
.qbar i{display:block;border-radius:1px}
.qval{text-align:right;font-size:12px}
.qrow.axis{border-top:0;padding-top:0}
.qaxis{display:flex;justify-content:space-between;font-size:10px;color:var(--secondary-text-color)}
.schema{width:100%;max-width:760px;display:block;margin:0 auto}
.schema .node{cursor:pointer}
.schema .node:hover rect{stroke-width:2.2}
.schema .node:focus{outline:none}
.nodedetail{margin-top:8px;padding:10px 12px;border-radius:10px;background:var(--secondary-background-color)}
a.copy{text-decoration:none}@media (max-width:600px){.round.refresh{display:none}.refresh-inline{display:flex}.grid3{grid-template-columns:repeat(2,minmax(0,1fr))}.battrow{grid-template-columns:minmax(0,1fr)}.qrow{grid-template-columns:minmax(0,1fr) 70px}.qrow .qbar{grid-column:1/-1;grid-row:2}.qrow.axis .qaxis{grid-column:1/-1}.cellrow{grid-template-columns:minmax(0,1fr)}
.kpis,.grid4{grid-template-columns:repeat(2,minmax(0,1fr))}.grid2,.ringrow{grid-template-columns:minmax(0,1fr)}.banner .title{font-size:15px}.banner.collapsed .tname{display:none}.banner:not(.collapsed) .titles{background:linear-gradient(90deg,var(--sky) 75%,transparent);padding-right:18px;position:relative;z-index:1}.barrow{grid-template-columns:80px minmax(0,1fr) 90px}}
`;

if (!customElements.get('energy-hub-panel')) {
  customElements.define('energy-hub-panel', EnergyHubPanel);
  console.info(`%c ENERGY-HUB %c v${ENERGY_HUB_PANEL_VERSION} `, 'color:#fff;background:#BA7517;font-weight:700', 'color:#BA7517;background:#fff');
}
