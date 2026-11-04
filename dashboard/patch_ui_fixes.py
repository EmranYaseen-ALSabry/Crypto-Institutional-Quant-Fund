from pathlib import Path
import re

p = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\dashboard\templates\index.html")
text = p.read_text(encoding="utf-8")

# 1. Fix .ltr-text in CSS to prevent table-cell breaking
old_css = """.ltr-text {
            direction: ltr;
            display: inline-block;
        }"""
new_css = """.ltr-text {
            direction: ltr;
            unicode-bidi: isolate;
        }"""
text = text.replace(old_css, new_css)

# 2. Fix Initial Placeholder in Opportunities table to not look like it's continuously spinning
old_opp_placeholder = """                            <tbody id="opportunities-tbody" class="divide-y divide-slate-800/60 font-mono">
                                <tr>
                                    <td colspan="10" class="py-12 text-center text-slate-400">
                                        <div class="flex flex-col items-center justify-center gap-3">
                                            <i data-lucide="loader-2" class="w-7 h-7 text-cyan-400 animate-spin"></i>
                                            <span class="text-sm font-sans">جاري مسح أسواق Binance وتحليل الفرص...</span>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>"""

new_opp_placeholder = """                            <tbody id="opportunities-tbody" class="divide-y divide-slate-800/60 font-mono">
                                <tr>
                                    <td colspan="10" class="py-12 text-center text-slate-400">
                                        <div class="flex flex-col items-center justify-center gap-3">
                                            <div class="w-12 h-12 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-cyan-400">
                                                <i data-lucide="radar" class="w-6 h-6"></i>
                                            </div>
                                            <span class="text-sm font-sans font-semibold text-slate-200">الرادار جاهز لمسح السوق واستكشاف الفرص</span>
                                            <p class="text-xs text-slate-400 font-sans max-w-md">اضغط على زر <span class="text-cyan-400 font-bold">"فحص يدوي الآن"</span> للبدء فوراً، أو فعّل <span class="text-emerald-400 font-bold">"الرادار التلقائي"</span> للبحث المجدول الدوري كل دقيقة.</p>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>"""
text = text.replace(old_opp_placeholder, new_opp_placeholder)

# 3. Stop auto-triggering scan when user switches to tab-scanner
old_switch = "if (tabId === 'tab-scanner') { fetchMarketOpportunities(); fetchTrackedPairs(); }"
new_switch = """if (tabId === 'tab-scanner') {
                fetchTrackedPairs();
                // Only scan automatically if Auto-Radar toggle is turned ON by user
                if (typeof autoRadarActive !== 'undefined' && autoRadarActive) {
                    fetchMarketOpportunities();
                }
            }"""
text = text.replace(old_switch, new_switch)

# 4. Fix Trades Table THEAD styling
old_trades_thead = """                        <table class="w-full text-right text-xs">
                            <thead class="bg-slate-900/90 text-slate-400 font-mono uppercase border-b border-slate-800">
                                <tr>
                                    <th class="p-3">#ID</th>
                                    <th class="p-3">المحرك Engine</th>
                                    <th class="p-3">الزوج Pair</th>
                                    <th class="p-3">النوع Side</th>
                                    <th class="p-3">سعر الدخول Entry</th>
                                    <th class="p-3">السعر الحالي Rate</th>
                                    <th class="p-3">الربح (%) PnL</th>
                                    <th class="p-3">الربح ($) USDT</th>
                                    <th class="p-3">حجم الصفقة Stake</th>
                                    <th class="p-3">تاريخ الفتح Open Date</th>
                                    <th class="p-3 text-center">إجراء فوري Action</th>
                                </tr>
                            </thead>"""

new_trades_thead = """                        <table class="w-full text-right text-xs border-collapse">
                            <thead class="bg-slate-900/90 text-slate-400 font-mono uppercase border-b border-slate-800 text-[11px]">
                                <tr>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap">#ID</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap">المحرك Engine</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap">الزوج Pair</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap">النوع Side</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap text-right">سعر الدخول Entry</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap text-right">السعر الحالي Rate</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap text-right">الربح (%) PnL</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap text-right">الربح ($) USDT</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap text-right">حجم الصفقة Stake</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap text-right">تاريخ الفتح Open Date</th>
                                    <th class="py-3.5 px-3.5 whitespace-nowrap text-center">إجراء فوري Action</th>
                                </tr>
                            </thead>"""
text = text.replace(old_trades_thead, new_trades_thead)

# 5. Fix Trades Table Row generation in fetchTrades()
old_trades_tbody_loop = """                    tr.innerHTML = `
                        <td class="p-3 font-bold text-slate-400">#${t.trade_id}</td>
                        <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold border ${engineBadge}">${t.engine}</span></td>
                        <td class="p-3 font-bold text-white ltr-text">${t.pair}</td>
                        <td class="p-3 font-bold ${sideBadge}">${t.side}</td>
                        <td class="p-3 text-slate-300 ltr-text">${t.open_rate}</td>
                        <td class="p-3 text-slate-200 font-bold ltr-text">${t.current_rate}</td>
                        <td class="p-3 font-bold ${pnlColor} ltr-text">${isProfit ? '+' : ''}${t.profit_pct}%</td>
                        <td class="p-3 font-bold ${pnlColor} ltr-text">${isProfit ? '+' : ''}$${t.profit_abs}</td>
                        <td class="p-3 text-slate-400 ltr-text">$${t.stake_amount}</td>
                        <td class="p-3 text-slate-500 text-[11px] ltr-text">${t.open_date}</td>
                        <td class="p-3 text-center">
                            <button onclick="forceExitTrade('${t.engine}', ${t.trade_id})" class="px-2.5 py-1 rounded bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800 text-[10px] font-bold transition">
                                إغلاق فوري
                            </button>
                        </td>
                    `;"""

new_trades_tbody_loop = """                    tr.className = 'hover:bg-slate-800/40 transition border-b border-slate-800/40';
                    tr.innerHTML = `
                        <td class="py-3 px-3.5 whitespace-nowrap font-bold text-slate-400 align-middle">#${t.trade_id}</td>
                        <td class="py-3 px-3.5 whitespace-nowrap align-middle"><span class="px-2 py-0.5 rounded text-[10px] font-bold border ${engineBadge}">${t.engine}</span></td>
                        <td class="py-3 px-3.5 whitespace-nowrap font-bold text-white font-mono align-middle" dir="ltr">${t.pair}</td>
                        <td class="py-3 px-3.5 whitespace-nowrap font-bold ${sideBadge} align-middle">${t.side}</td>
                        <td class="py-3 px-3.5 whitespace-nowrap text-slate-300 font-mono align-middle" dir="ltr">${t.open_rate}</td>
                        <td class="py-3 px-3.5 whitespace-nowrap text-slate-100 font-bold font-mono align-middle" dir="ltr">${t.current_rate}</td>
                        <td class="py-3 px-3.5 whitespace-nowrap font-bold ${pnlColor} font-mono align-middle" dir="ltr">${isProfit ? '+' : ''}${t.profit_pct}%</td>
                        <td class="py-3 px-3.5 whitespace-nowrap font-bold ${pnlColor} font-mono align-middle" dir="ltr">${isProfit ? '+' : ''}$${t.profit_abs}</td>
                        <td class="py-3 px-3.5 whitespace-nowrap text-slate-300 font-mono align-middle" dir="ltr">$${t.stake_amount}</td>
                        <td class="py-3 px-3.5 whitespace-nowrap text-slate-400 text-[11px] font-mono align-middle" dir="ltr">${t.open_date}</td>
                        <td class="py-3 px-3.5 whitespace-nowrap text-center align-middle">
                            <button onclick="forceExitTrade('${t.engine}', ${t.trade_id})" class="px-3 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800 text-xs font-bold transition">
                                إغلاق فوري
                            </button>
                        </td>
                    `;"""
text = text.replace(old_trades_tbody_loop, new_trades_tbody_loop)

p.write_text(text, encoding="utf-8")
print("Successfully patched UI fixes in index.html!")
