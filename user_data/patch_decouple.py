from pathlib import Path

p = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\user_data\strategies\InstitutionalDualStrategy.py")
text = p.read_text(encoding="utf-8")

# 1. Add bot_loop_start before populate_indicators
bot_loop_func = """    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        \"\"\"
        Executed on the main thread at each bot iteration.
        Safely caches active open trade parameters to avoid SQLite lock contention during multi-pair analysis.
        \"\"\"
        try:
            from freqtrade.persistence import Trade
            open_trades = Trade.get_trades([Trade.is_open.is_(True)]).all()
            cache = {}
            for t in open_trades:
                cache[t.pair] = {
                    'open_rate': float(t.open_rate),
                    'stop_loss': float(t.stop_loss) if t.stop_loss else None,
                    'is_short': getattr(t, 'is_short', False)
                }
            self._open_trades_cache = cache
        except Exception:
            if not hasattr(self, '_open_trades_cache'):
                self._open_trades_cache = {}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:"""

text = text.replace("    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:", bot_loop_func, 1)

# 2. Replace trade query inside populate_indicators
old_query = """        # Active Trade Visual Overlay Lines (Entry, Stop-Loss, TP1, TP2)
        try:
            open_trades = []
            try:
                open_trades = Trade.get_trades([Trade.pair == metadata['pair'], Trade.is_open.is_(True)]).all()
            except Exception:
                pass

            if open_trades:
                active_trade = open_trades[-1]
                t_entry = float(active_trade.open_rate)
                t_sl = float(active_trade.stop_loss) if active_trade.stop_loss else (t_entry * (1 - 0.04) if not active_trade.is_short else t_entry * (1 + 0.04))
                t_short = getattr(active_trade, 'is_short', False)
                if not t_short:
                    t_tp1 = t_entry * 1.015
                    t_tp2 = t_entry * 1.030
                else:
                    t_tp1 = t_entry * 0.985
                    t_tp2 = t_entry * 0.970

                dataframe['trade_entry'] = t_entry
                dataframe['trade_stoploss'] = t_sl
                dataframe['trade_tp1'] = t_tp1
                dataframe['trade_tp2'] = t_tp2"""

new_query = """        # Active Trade Visual Overlay Lines (Entry, Stop-Loss, TP1, TP2)
        try:
            active_trade = getattr(self, '_open_trades_cache', {}).get(metadata['pair'])
            if active_trade:
                t_entry = active_trade['open_rate']
                t_short = active_trade['is_short']
                t_sl = active_trade['stop_loss'] if active_trade['stop_loss'] else (t_entry * (0.96 if not t_short else 1.04))
                if not t_short:
                    t_tp1 = t_entry * 1.015
                    t_tp2 = t_entry * 1.030
                else:
                    t_tp1 = t_entry * 0.985
                    t_tp2 = t_entry * 0.970

                dataframe['trade_entry'] = t_entry
                dataframe['trade_stoploss'] = t_sl
                dataframe['trade_tp1'] = t_tp1
                dataframe['trade_tp2'] = t_tp2"""

text = text.replace(old_query, new_query, 1)

p.write_text(text, encoding="utf-8")
print("Successfully decoupled trade indicators from SQLite!")
