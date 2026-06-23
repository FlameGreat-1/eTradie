
softverse@Softverse:~/eTradie$ # What's the top-level dir, and does it carry a Deriv servers.dat?
unzip -l /tmp/deriv.zip | head -20
unzip -l /tmp/deriv.zip | grep -iE 'servers\.dat|MetaTrader'

# Extract just servers.dat and confirm it has Deriv entries
mkdir -p /tmp/derivchk && cd /tmp/derivchk
unzip -o /tmp/deriv.zip '*/config/servers.dat' >/dev/null 2>&1 || unzip -o /tmp/deriv.zip '*servers.dat' >/dev/null 2>&1
find /tmp/derivchk -iname servers.dat
SD=$(find /tmp/derivchk -iname servers.dat | head -1)
grep -aiE 'deriv' "$SD" | head
Archive:  /tmp/deriv.zip
  Length      Date    Time    Name
---------  ---------- -----   ----
        0  2026-06-22 00:18   MetaTrader 5/
   410598  2026-06-21 22:45   MetaTrader 5/Terminal.ico
 21221584  2026-06-21 22:45   MetaTrader 5/metatester64.exe
        0  2026-06-22 00:09   MetaTrader 5/Bases/
      428  2026-06-22 00:15   MetaTrader 5/Bases/books.dat
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/history/
        0  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/cache/
  1314734  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/cache/H1.hc
 22397661  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/2025.hcc
 22456050  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/2024.hcc
 32258805  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/2023.hcc
 10485096  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/2026.hcc
        0  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/cache/
  1314494  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/cache/H1.hc
        0  2026-06-22 00:18   MetaTrader 5/
   410598  2026-06-21 22:45   MetaTrader 5/Terminal.ico
 21221584  2026-06-21 22:45   MetaTrader 5/metatester64.exe
        0  2026-06-22 00:09   MetaTrader 5/Bases/
      428  2026-06-22 00:15   MetaTrader 5/Bases/books.dat
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/history/
        0  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/cache/
  1314734  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/cache/H1.hc
 22397661  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/2025.hcc
 22456050  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/2024.hcc
 32258805  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/2023.hcc
 10485096  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/USDJPY/2026.hcc
        0  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/cache/
  1314494  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/cache/H1.hc
 22399701  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/2025.hcc
 22492050  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/2024.hcc
 32219058  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/2023.hcc
 10485336  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/EURUSD/2026.hcc
        0  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/GBPUSD/
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/history/GBPUSD/cache/
  1314494  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/GBPUSD/cache/H1.hc
 22397661  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/GBPUSD/2025.hcc
 22478850  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/GBPUSD/2024.hcc
 32293665  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/GBPUSD/2023.hcc
 10484256  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/GBPUSD/2026.hcc
        0  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDCHF/
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/history/USDCHF/cache/
  1314374  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/USDCHF/cache/H1.hc
 22405341  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDCHF/2025.hcc
 22446930  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDCHF/2024.hcc
 32280225  2026-06-22 00:10   MetaTrader 5/Bases/Deriv-Demo/history/USDCHF/2023.hcc
 10481976  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/history/USDCHF/2026.hcc
     2138  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/tickers.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/news/
      428  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/news/news.dat
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/mail/
    45183  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/mail/mail-201415706.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/subscriptions/
     4096  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/subscriptions/subscriptions-201415706.dat
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/trades/
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/trades/201415706/
     8724  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/trades/201415706/history_2026.06.dat
     4096  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/trades/201415706/cache.dat
     8512  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/trades/201415706/deals_2026.04.dat
   106432  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/trades/201415706/deals_2026.05.dat
    13876  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/trades/201415706/history_2026.04.dat
   105968  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/trades/201415706/history_2026.05.dat
     7152  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/trades/201415706/deals_2026.06.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDSEK/
    45132  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDSEK/ticks.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDJPY/
    14292  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDJPY/ticks.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/NZDUSD/
    17352  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/NZDUSD/ticks.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/EURUSD/
    35892  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/EURUSD/ticks.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDCAD/
    32592  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDCAD/ticks.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/AUDUSD/
     9852  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/AUDUSD/ticks.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/GBPUSD/
    25332  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/GBPUSD/ticks.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDCHF/
     8112  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDCHF/ticks.dat
        0  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDCNH/
     4092  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/ticks/USDCNH/ticks.dat
        0  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/symbols/
   786432  2026-06-22 00:09   MetaTrader 5/Bases/Deriv-Demo/symbols/symbols-201415706.dat
     9842  2026-06-22 00:15   MetaTrader 5/Bases/Deriv-Demo/symbols/selected-201415706.dat
     2544  2026-06-22 00:15   MetaTrader 5/Bases/objects.dat
      428  2026-06-22 00:15   MetaTrader 5/Bases/options.dat
      432  2026-06-22 00:15   MetaTrader 5/Bases/alerts.dat
    32328  2026-06-22 00:15   MetaTrader 5/Bases/strategy.dat
    25816  2026-06-22 00:15   MetaTrader 5/Bases/indicators.dat
        0  2026-06-22 00:09   MetaTrader 5/Bases/signals/
  3936632  2026-06-22 00:09   MetaTrader 5/Bases/signals/signals.dat
        0  2026-06-21 22:46   MetaTrader 5/Bases/Default/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/news/
      428  2026-06-22 00:09   MetaTrader 5/Bases/Default/news/news.dat
        0  2026-06-21 22:46   MetaTrader 5/Bases/Default/subscriptions/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/Mail/
     9818  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.bengali.welcome
     9082  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.default.welcome
     8360  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.serbian.welcome
    10314  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.german.welcome
    10252  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.greek.welcome
    21460  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.russian.welcome
     9122  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.mongolian.welcome
     7666  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.polish.welcome
    20066  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.croatian.welcome
     9690  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.bulgarian.welcome
    12368  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.finnish.welcome
    11398  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.punjabi (pakistan).welcome
    21070  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.ukrainian.welcome
    16806  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.marathi.welcome
     9758  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.polish.welcome
     9024  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.mongolian.welcome
    12160  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.greek.welcome
     9212  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.polish.welcome
     8832  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.swahili.welcome
     9312  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.tamil.welcome
     8048  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.hebrew.welcome
    19738  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.marathi.welcome
     9324  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.punjabi (pakistan).welcome
     9974  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.turkish.welcome
     9762  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.danish.welcome
     9614  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.thai.welcome
     9226  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.danish.welcome
     7532  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.hindi.welcome
     9464  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.hebrew.welcome
     7870  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.italian.welcome
     7360  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.arabic.welcome
    20154  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.lithuanian.welcome
     9698  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.mongolian.welcome
     7682  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.uzbek.welcome
    19636  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.arabic.welcome
     8522  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.danish.welcome
    18476  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.portuguese.welcome
     7146  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.chinese (traditional).welcome
    10356  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.italian.welcome
    20286  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.persian.welcome
    19470  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.hindi.welcome
    21180  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.bulgarian.welcome
    11184  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.persian.welcome
    11928  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.tajik.welcome
     9082  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.malay.welcome
    10088  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.javanese.welcome
     7604  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.punjabi (pakistan).welcome
     8756  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.swedish.welcome
     6976  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.japanese.welcome
     9146  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.spanish.welcome
    17960  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.japanese.welcome
    11568  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.polish.welcome
    10058  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.georgian.welcome
     9952  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.croatian.welcome
     9866  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.marathi.welcome
    17278  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.chinese (traditional).welcome
    21798  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.czech.welcome
    10276  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.uzbek.welcome
     9718  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.bengali.welcome
     9912  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.english.welcome
    20752  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.swedish.welcome
    20796  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.dutch.welcome
     7500  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.bengali.welcome
    17052  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.latvian.welcome
    10338  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.tajik.welcome
     9434  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.thai.welcome
     7904  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.turkish.welcome
     9398  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.russian.welcome
    20082  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.serbian.welcome
     8532  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.malay.welcome
     7652  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.default.welcome
    20130  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.bengali.welcome
     8380  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.punjabi (india).welcome
    11418  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.slovenian.welcome
    10414  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.slovak.welcome
    17118  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.arabic.welcome
     8102  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.chinese (simplified).welcome
    20720  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.telugu.welcome
     8554  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.chinese (traditional).welcome
     9266  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.bulgarian.welcome
     9358  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.portuguese.welcome
     7476  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.korean.welcome
    18886  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.chinese (simplified).welcome
     7760  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.tajik.welcome
     9726  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.javanese.welcome
    19942  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.arabic.welcome
     9522  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.french.welcome
     9736  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.latvian.welcome
     8876  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.estonian.welcome
     9840  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.ukrainian.welcome
    16304  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.chinese (traditional).welcome
     9788  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.hindi.welcome
    10210  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.portuguese.welcome
    17004  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.javanese.welcome
    17936  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.chinese (traditional).welcome
     8734  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.italian.welcome
    17270  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.romanian.welcome
    17258  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.greek.welcome
     8754  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.greek.welcome
    12468  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.portuguese.welcome
    16790  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.thai.welcome
    10154  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.default.welcome
     8318  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.bengali.welcome
     9566  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.italian.welcome
    21256  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.german.welcome
    12908  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.spanish.welcome
     8946  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.korean.welcome
    11348  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.croatian.welcome
     8600  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.hebrew.welcome
    10636  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.french.welcome
     7456  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.mongolian.welcome
     8874  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.marathi.welcome
    20212  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.ukrainian.welcome
    17050  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.estonian.welcome
    22552  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.hungarian.welcome
     8104  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.chinese (traditional).welcome
     7642  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.telugu.welcome
     9786  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.lithuanian.welcome
    20864  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.english.welcome
     7700  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.ukrainian.welcome
     7542  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.hausa.welcome
    11784  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.swahili.welcome
     9046  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.estonian.welcome
     9348  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.georgian.welcome
    17238  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.chinese (simplified).welcome
    18310  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.english.welcome
    17348  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.tamil.welcome
    11100  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.spanish.welcome
    17080  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.polish.welcome
     7432  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.marathi.welcome
    20300  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.malay.welcome
    10618  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.hebrew.welcome
     9218  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.polish.welcome
     8652  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.hausa.welcome
     7470  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.estonian.welcome
     8580  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.polish.welcome
     8516  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.lithuanian.welcome
    19910  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.indonesian.welcome
    16854  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.punjabi (pakistan).welcome
     9202  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.russian.welcome
    10600  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.czech.welcome
     8918  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.slovenian.welcome
     9644  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.croatian.welcome
     8620  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.tajik.welcome
    10206  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.danish.welcome
     8268  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.vietnamese.welcome
    19120  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.thai.welcome
     7550  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.malay.welcome
    17184  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.persian.welcome
    17202  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.telugu.welcome
    19248  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.thai.welcome
     7960  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.slovak.welcome
    20600  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.danish.welcome
    17518  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.japanese.welcome
    11468  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.arabic.welcome
    21258  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.italian.welcome
    11418  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.javanese.welcome
    12366  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.french.welcome
     8486  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.punjabi (pakistan).welcome
     8120  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.french.welcome
    10620  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.slovak.welcome
    18346  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.tajik.welcome
    45002  2026-06-21 22:47   MetaTrader 5/Bases/Default/Mail/mail-0.dat
     9530  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.japanese.welcome
    20622  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.bulgarian.welcome
    20538  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.turkish.welcome
     9946  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.latvian.welcome
     9100  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.punjabi (india).welcome
    21054  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.dutch.welcome
     9828  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.punjabi (india).welcome
     8340  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.korean.welcome
    17064  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.danish.welcome
     8444  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.marathi.welcome
    11578  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.turkish.welcome
    10242  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.swedish.welcome
    11692  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.indonesian.welcome
    10148  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.estonian.welcome
    20880  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.italian.welcome
     9152  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.serbian.welcome
     9906  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.slovak.welcome
    19946  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.finnish.welcome
    10112  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.swahili.welcome
    12066  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.tamil.welcome
    12098  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.swedish.welcome
    18396  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.dutch.welcome
     9996  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.bulgarian.welcome
    20806  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.portuguese.welcome
     8766  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.thai.welcome
    21418  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.german.welcome
    19976  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.hindi.welcome
     8818  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.arabic.welcome
    11478  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.english.welcome
     9542  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.german.welcome
     9942  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.indonesian.welcome
     8410  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.hindi.welcome
     6372  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.chinese (traditional).welcome
     9240  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.vietnamese.welcome
    10676  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.russian.welcome
     9050  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.croatian.welcome
     6702  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.japanese.welcome
    21030  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.tajik.welcome
    18270  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.ukrainian.welcome
     8088  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.hebrew.welcome
    20152  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.greek.welcome
     9052  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.latvian.welcome
     7886  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.bulgarian.welcome
    20496  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.polish.welcome
     8934  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.slovenian.welcome
     8502  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.chinese (traditional).welcome
     8142  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.thai.welcome
     7958  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.german.welcome
    11606  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.ukrainian.welcome
     9978  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.urdu.welcome
     9536  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.punjabi (india).welcome
     9364  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.tamil.welcome
     9220  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.hebrew.welcome
     9256  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.indonesian.welcome
    21610  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.vietnamese.welcome
     9482  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.spanish.welcome
    19750  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.punjabi (pakistan).welcome
     9140  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.tajik.welcome
     7342  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.japanese.welcome
    10024  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.malay.welcome
     9640  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.malay.welcome
    19854  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.estonian.welcome
     9194  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.dutch.welcome
    18726  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.french.welcome
    10930  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.thai.welcome
    21734  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.spanish.welcome
    17372  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.czech.welcome
     7586  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.urdu.welcome
     7392  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.latvian.welcome
     9514  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.swedish.welcome
     7864  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.tamil.welcome
    17218  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.finnish.welcome
     9916  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.romanian.welcome
     7468  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.lithuanian.welcome
    20830  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.finnish.welcome
     8924  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.romanian.welcome
    11308  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.marathi.welcome
     9856  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.telugu.welcome
    10092  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.french.welcome
     8574  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.persian.welcome
     9296  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.urdu.welcome
     7478  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.punjabi (india).welcome
    18890  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.hebrew.welcome
     7458  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.slovenian.welcome
     9044  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.punjabi (pakistan).welcome
    21484  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.french.welcome
    20668  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.uzbek.welcome
    17068  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.swahili.welcome
     7796  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.dutch.welcome
    10206  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.dutch.welcome
    10674  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.vietnamese.welcome
    10068  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.russian.welcome
     9238  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.dutch.welcome
     9986  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.finnish.welcome
    10418  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.tamil.welcome
    10378  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.spanish.welcome
     8538  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.swahili.welcome
     9666  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.german.welcome
    11844  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.bulgarian.welcome
     7772  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.swedish.welcome
     7748  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.greek.welcome
     9354  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.romanian.welcome
    20396  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.mongolian.welcome
    10244  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.vietnamese.welcome
    17136  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.mongolian.welcome
    10278  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.french.welcome
     7940  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.finnish.welcome
     7652  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.english.welcome
    10082  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.tamil.welcome
     7798  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.russian.welcome
     7046  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.hebrew.welcome
    19196  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.japanese.welcome
     9554  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.korean.welcome
     9546  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.spanish.welcome
    10158  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.persian.welcome
     7588  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.danish.welcome
    20632  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.vietnamese.welcome
    18444  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.italian.welcome
     9598  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.finnish.welcome
    10104  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.mongolian.welcome
    19674  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.urdu.welcome
    20506  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.russian.welcome
    19768  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.polish.welcome
     9944  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.swedish.welcome
     9216  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.malay.welcome
     8814  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.dutch.welcome
    21312  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.hungarian.welcome
    21072  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.romanian.welcome
     8972  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.hindi.welcome
    20750  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.indonesian.welcome
    19800  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.swahili.welcome
     7606  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.persian.welcome
     8410  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.hungarian.welcome
    19520  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.marathi.welcome
    17166  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.swedish.welcome
    12928  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.czech.welcome
     7480  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.serbian.welcome
    11382  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.urdu.welcome
     8984  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.finnish.welcome
     9674  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.serbian.welcome
    18494  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.german.welcome
    20298  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.latvian.welcome
     7266  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.thai.welcome
     8276  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.japanese.welcome
    17138  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.georgian.welcome
    17474  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.vietnamese.welcome
     9950  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.slovenian.welcome
     6708  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.korean.welcome
     7708  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.indonesian.welcome
    11666  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.telugu.welcome
     6368  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.chinese (simplified).welcome
     9080  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.default.welcome
     9504  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.portuguese.welcome
    10154  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.english.welcome
    20488  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.estonian.welcome
     9720  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.estonian.welcome
     8996  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.punjabi (india).welcome
    11824  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.uzbek.welcome
     8074  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.thai.welcome
     9188  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.bulgarian.welcome
    17726  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.hungarian.welcome
     8454  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.javanese.welcome
    18568  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.spanish.welcome
    12184  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.german.welcome
    20992  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.spanish.welcome
    19626  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.latvian.welcome
     9220  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.hausa.welcome
    10238  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.finnish.welcome
    10020  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.serbian.welcome
     9642  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.urdu.welcome
     8848  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.chinese (simplified).welcome
    10144  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.italian.welcome
    20782  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.hausa.welcome
     9304  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.greek.welcome
    20476  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.telugu.welcome
    19988  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.korean.welcome
    20226  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.bengali.welcome
     9028  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.ukrainian.welcome
    10022  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.polish.welcome
    10376  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.hausa.welcome
    10012  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.tajik.welcome
     8766  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.estonian.welcome
    10280  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.dutch.welcome
    10420  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.czech.welcome
     9100  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.portuguese.welcome
    20864  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.default.welcome
     9052  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.lithuanian.welcome
    13152  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.vietnamese.welcome
    17286  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.indonesian.welcome
     6416  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.chinese (simplified).welcome
    19702  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.mongolian.welcome
     9810  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.hungarian.welcome
    21522  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.portuguese.welcome
     7896  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.romanian.welcome
    10860  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.hungarian.welcome
    19536  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.danish.welcome
    10386  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.romanian.welcome
    16846  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.punjabi (india).welcome
    11838  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.dutch.welcome
     8472  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.default.welcome
    20436  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.english.welcome
    19858  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.swedish.welcome
     9528  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.greek.welcome
    20024  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.punjabi (india).welcome
    12782  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.slovak.welcome
    20108  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.slovenian.welcome
     8914  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.japanese.welcome
    16850  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.urdu.welcome
    20808  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.turkish.welcome
    13682  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.hungarian.welcome
     8832  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.russian.welcome
     8592  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.georgian.welcome
    11796  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.georgian.welcome
     8278  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.arabic.welcome
    10660  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.vietnamese.welcome
     9212  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.ukrainian.welcome
     9852  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.greek.welcome
     8926  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.french.welcome
     9694  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.hungarian.welcome
     8838  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.uzbek.welcome
    10284  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.ukrainian.welcome
     8432  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.croatian.welcome
     8922  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.chinese (traditional).welcome
    19924  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.georgian.welcome
    21002  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.tamil.welcome
     8612  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.ukrainian.welcome
    19770  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.lithuanian.welcome
    21508  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.slovak.welcome
     6416  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.chinese (traditional).welcome
     9276  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.turkish.welcome
     8966  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.telugu.welcome
     9872  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.georgian.welcome
    11852  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.hausa.welcome
    12370  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.russian.welcome
     8674  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.telugu.welcome
     9998  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.lithuanian.welcome
     9124  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.persian.welcome
     8402  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.slovenian.welcome
     9612  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.punjabi (pakistan).welcome
     7144  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.chinese (simplified).welcome
     9042  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.swahili.welcome
     8664  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.indonesian.welcome
     9026  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.turkish.welcome
     8916  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.hindi.welcome
    12632  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.romanian.welcome
    20520  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.georgian.welcome
     8792  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.tamil.welcome
    17398  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.korean.welcome
    16930  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.croatian.welcome
    10258  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.turkish.welcome
    10200  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.indonesian.welcome
    17274  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.lithuanian.welcome
    18470  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.uzbek.welcome
    10844  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.hungarian.welcome
     9874  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.czech.welcome
    20704  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.czech.welcome
     8484  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.latvian.welcome
     7910  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.czech.welcome
    19610  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.malay.welcome
    21464  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.french.welcome
     9184  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.swedish.welcome
     7504  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.croatian.welcome
     9080  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.english.welcome
     9666  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.uzbek.welcome
     9960  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.hausa.welcome
    19652  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.croatian.welcome
     9084  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.georgian.welcome
    19980  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.javanese.welcome
     8964  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.javanese.welcome
     8868  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.bengali.welcome
     9912  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.default.welcome
     9096  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.hausa.welcome
     8910  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.javanese.welcome
     8904  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.japanese.welcome
     8612  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.turkish.welcome
     9154  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.danish.welcome
     8986  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.urdu.welcome
     9772  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.swahili.welcome
     9820  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.persian.welcome
    16728  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.hebrew.welcome
    17290  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.hausa.welcome
     7454  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.javanese.welcome
     9450  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.marathi.welcome
    11600  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.mongolian.welcome
     9000  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.croatian.welcome
     7610  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.swahili.welcome
     8814  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.german.welcome
    12116  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.italian.welcome
     9278  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.indonesian.welcome
     9910  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.punjabi (pakistan).welcome
     9372  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.slovak.welcome
     9238  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.italian.welcome
    18310  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.default.welcome
    18372  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.bulgarian.welcome
     8550  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.chinese (simplified).welcome
    16952  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.serbian.welcome
    11674  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.latvian.welcome
    10128  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.telugu.welcome
    20054  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.tamil.welcome
     8990  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.latvian.welcome
    11574  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.malay.welcome
    19732  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.persian.welcome
    11296  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.bengali.welcome
     9598  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.slovenian.welcome
     7570  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.georgian.welcome
    20628  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.swahili.welcome
    10498  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.bulgarian.welcome
     8236  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.arabic.welcome
     9446  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.czech.welcome
    10048  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.romanian.welcome
     8724  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.marathi.welcome
     8926  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.slovak.welcome
    11276  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.hindi.welcome
     8256  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.persian.welcome
    17066  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.malay.welcome
    10854  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.portuguese.welcome
     9906  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.arabic.welcome
    11362  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.serbian.welcome
     8398  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.urdu.welcome
    11608  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.lithuanian.welcome
    19680  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.serbian.welcome
    18386  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.russian.welcome
    11472  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.hungarian.welcome
     9046  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.telugu.welcome
    11398  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.danish.welcome
     8962  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.korean.welcome
    20162  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.romanian.welcome
    11154  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.punjabi (india).welcome
    20552  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.urdu.welcome
     9606  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.arabic.welcome
    20432  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.slovak.welcome
    17412  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.slovak.welcome
    20778  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.greek.welcome
    20582  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.punjabi (pakistan).welcome
    18132  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.turkish.welcome
     8866  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.czech.welcome
     9070  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.bengali.welcome
     8180  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.portuguese.welcome
    16944  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.slovenian.welcome
    19638  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.slovenian.welcome
    19602  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.javanese.welcome
    17254  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.chinese (simplified).welcome
     9082  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.english.welcome
    11478  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.default.welcome
    10570  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.uzbek.welcome
     8500  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.chinese (simplified).welcome
    19038  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.hebrew.welcome
    19612  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.punjabi (india).welcome
    11918  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/6.virtualhosting.estonian.welcome
     8768  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.finnish.welcome
     8472  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.english.welcome
    20268  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.hausa.welcome
    18124  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/10.developers.korean.welcome
    10480  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/3.market.german.welcome
    16842  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.hindi.welcome
     9554  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/2.signals.hindi.welcome
     9252  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.uzbek.welcome
     8120  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/9.payments.spanish.welcome
     9110  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.lithuanian.welcome
     8562  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/8.reports.mongolian.welcome
    17010  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/4.mobile.bengali.welcome
     9796  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.vietnamese.welcome
     9140  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/5.freelance.serbian.welcome
     7138  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/7.risk-warning.korean.welcome
    21100  2026-06-21 22:45   MetaTrader 5/Bases/Default/Mail/1.welcome.uzbek.welcome
        0  2026-06-21 22:46   MetaTrader 5/Bases/Default/trades/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/trades/0/
     4096  2026-06-21 23:28   MetaTrader 5/Bases/Default/trades/0/cache.dat
        0  2026-06-21 22:45   MetaTrader 5/Bases/Default/Symbols/
    15072  2026-06-22 00:09   MetaTrader 5/Bases/Default/Symbols/selected-0.dat
  4870144  2026-06-21 22:45   MetaTrader 5/Bases/Default/Symbols/symbols-0.dat
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/ticks/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/ticks/EURUSD/
        0  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/History/USDJPY/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/History/USDJPY/cache/
   406898  2026-06-22 00:09   MetaTrader 5/Bases/Default/History/USDJPY/cache/H1.hc
 16251036  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/USDJPY/2024.hcc
  9909846  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/USDJPY/2023.hcc
    15333  2026-06-22 00:09   MetaTrader 5/Bases/Default/History/USDJPY/2026.hcc
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/History/EURUSD/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/History/EURUSD/cache/
   406880  2026-06-22 00:09   MetaTrader 5/Bases/Default/History/EURUSD/cache/H1.hc
 14518323  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/EURUSD/2024.hcc
  9827739  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/EURUSD/2023.hcc
    15333  2026-06-22 00:09   MetaTrader 5/Bases/Default/History/EURUSD/2026.hcc
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/History/GBPUSD/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/History/GBPUSD/cache/
   406898  2026-06-22 00:09   MetaTrader 5/Bases/Default/History/GBPUSD/cache/H1.hc
 16253196  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/GBPUSD/2024.hcc
  9913566  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/GBPUSD/2023.hcc
    15333  2026-06-22 00:09   MetaTrader 5/Bases/Default/History/GBPUSD/2026.hcc
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/History/USDCHF/
        0  2026-06-21 22:47   MetaTrader 5/Bases/Default/History/USDCHF/cache/
   406880  2026-06-22 00:09   MetaTrader 5/Bases/Default/History/USDCHF/cache/H1.hc
 15232056  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/USDCHF/2024.hcc
  9907746  2026-06-21 22:45   MetaTrader 5/Bases/Default/History/USDCHF/2023.hcc
    15333  2026-06-22 00:09   MetaTrader 5/Bases/Default/History/USDCHF/2026.hcc
        0  2026-06-21 22:46   MetaTrader 5/Bases/Custom/
        0  2026-06-21 22:46   MetaTrader 5/Bases/Custom/history/
        0  2026-06-21 22:46   MetaTrader 5/Bases/Custom/ticks/
        0  2026-06-22 00:18   MetaTrader 5/config/
        0  2026-06-22 00:18   MetaTrader 5/config/certificates/
     4558  2026-06-22 00:19   MetaTrader 5/config/terminal.ini
    12108  2026-06-22 00:15   MetaTrader 5/config/agents.dat
      586  2026-06-22 00:18   MetaTrader 5/config/common.ini
     7220  2026-06-22 00:15   MetaTrader 5/config/accounts.dat
     5908  2026-06-22 00:15   MetaTrader 5/config/settings.ini
   396008  2026-06-22 00:20   MetaTrader 5/config/dnsperf.dat
        2  2026-06-22 00:15   MetaTrader 5/config/hotkeys.ini
   169004  2026-06-22 00:11   MetaTrader 5/config/servers.dat
118840976  2026-06-21 22:45   MetaTrader 5/terminal64.exe
        0  2026-06-22 00:10   MetaTrader 5/Config/
        0  2026-06-21 22:46   MetaTrader 5/Config/certificates/
    16908  2026-06-22 00:09   MetaTrader 5/Config/terminal.ini
    12108  2026-06-21 23:28   MetaTrader 5/Config/agents.dat
     1162  2026-06-22 00:09   MetaTrader 5/Config/common.ini
     7220  2026-06-22 00:09   MetaTrader 5/Config/accounts.dat
    36018  2026-06-21 22:45   MetaTrader 5/Config/terminal.lic
     5908  2026-06-21 23:28   MetaTrader 5/Config/settings.ini
   396008  2026-06-22 00:05   MetaTrader 5/Config/dnsperf.dat
        2  2026-06-21 23:28   MetaTrader 5/Config/hotkeys.ini
   169004  2026-06-22 00:10   MetaTrader 5/Config/servers.dat
        0  2026-06-21 22:46   MetaTrader 5/Tester/
        0  2026-06-21 22:45   MetaTrader 5/Profiles/
        0  2026-06-21 22:45   MetaTrader 5/Profiles/SymbolSets/
       64  2026-06-21 22:45   MetaTrader 5/Profiles/SymbolSets/forex.major.set
      288  2026-06-21 22:45   MetaTrader 5/Profiles/SymbolSets/forex.all.set
      218  2026-06-21 22:45   MetaTrader 5/Profiles/SymbolSets/forex.crosses.set
        0  2026-06-21 22:45   MetaTrader 5/Profiles/Templates/
     4082  2026-06-21 22:45   MetaTrader 5/Profiles/Templates/ADX.tpl
     7214  2026-06-21 22:45   MetaTrader 5/Profiles/Templates/Momentum.tpl
     4866  2026-06-21 22:45   MetaTrader 5/Profiles/Templates/BollingerBands.tpl
        0  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/
        0  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/British Pound/
     4434  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/British Pound/chart01.chr
     4434  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/British Pound/chart04.chr
      106  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/British Pound/order.wnd
     4432  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/British Pound/chart03.chr
     4432  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/British Pound/chart02.chr
        0  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Default/
     2766  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Default/chart01.chr
     3050  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Default/chart04.chr
      106  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Default/order.wnd
     3174  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Default/chart03.chr
     2766  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Default/chart02.chr
        0  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Euro/
     4434  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Euro/chart01.chr
     4434  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Euro/chart04.chr
      106  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Euro/order.wnd
     4432  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Euro/chart03.chr
     4432  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Euro/chart02.chr
        0  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Market Overview/
     5652  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Market Overview/chart01.chr
     3168  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Market Overview/chart04.chr
      106  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Market Overview/order.wnd
     3022  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Market Overview/chart03.chr
     3166  2026-06-21 22:45   MetaTrader 5/Profiles/Charts/Market Overview/chart02.chr
        0  2026-06-22 00:02   MetaTrader 5/logs/
     4988  2026-06-21 23:59   MetaTrader 5/logs/20260621.log
    10140  2026-06-22 00:18   MetaTrader 5/logs/20260622.log
    66980  2026-06-21 23:00   MetaTrader 5/logs/metaeditor.log
        0  2026-06-21 22:45   MetaTrader 5/Sounds/
    26758  2026-06-21 22:45   MetaTrader 5/Sounds/email.wav
    25816  2026-06-21 22:45   MetaTrader 5/Sounds/news.wav
     5212  2026-06-21 22:45   MetaTrader 5/Sounds/stops.wav
    20712  2026-06-21 22:45   MetaTrader 5/Sounds/timeout.wav
    13250  2026-06-21 22:45   MetaTrader 5/Sounds/connect.wav
     7740  2026-06-21 22:45   MetaTrader 5/Sounds/disconnect.wav
     5212  2026-06-21 22:45   MetaTrader 5/Sounds/wait.wav
    13402  2026-06-21 22:45   MetaTrader 5/Sounds/request.wav
    22676  2026-06-21 22:45   MetaTrader 5/Sounds/tick.wav
    16620  2026-06-21 22:45   MetaTrader 5/Sounds/alert.wav
    20114  2026-06-21 22:45   MetaTrader 5/Sounds/alert2.wav
     2558  2026-06-21 22:45   MetaTrader 5/Sounds/ok.wav
     2842  2026-06-21 22:45   MetaTrader 5/Sounds/expert.wav
        0  2026-06-21 22:47   MetaTrader 5/MQL5/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/
   153178  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/ExpertMAPSAR.ex5
   157446  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/ExpertMAPSARSizeOptimized.ex5
   153738  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/ExpertMAMA.ex5
   144382  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/ExpertMACD.ex5
     6710  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/ExpertMAPSARSizeOptimized.mq5
     6074  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/ExpertMACD.mq5
     6342  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/ExpertMAPSAR.mq5
     6427  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Advisors/ExpertMAMA.mq5
        0  2026-06-21 22:59   MetaTrader 5/MQL5/Experts/Free Robots/
    25066  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Engulfing MFI.mq5
    25140  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Harami MFI.mq5
    24583  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/HangingMan Hammer MFI.mq5
    49380  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Harami Stoch.ex5
    23591  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish MeetingLines MFI.mq5
    24583  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/HangingMan Hammer CCI.mq5
    48136  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/DarkCloud PiercingLine CCI.ex5
    24592  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/HangingMan Hammer RSI.mq5
    48380  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/HangingMan Hammer RSI.ex5
    25064  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Engulfing RSI.mq5
    50070  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/DarkCloud PiercingLine Stoch.ex5
    46772  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish MeetingLines MFI.ex5
    47924  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/DarkCloud PiercingLine RSI.ex5
    49220  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/HangingMan Hammer CCI.ex5
    25013  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/DarkCloud PiercingLine CCI.mq5
    26170  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/MorningEvening StarDoji MFI.mq5
    48194  2026-06-21 22:59   MetaTrader 5/MQL5/Experts/Free Robots/MorningEvening StarDoji MFI.ex5
    48774  2026-06-21 22:59   MetaTrader 5/MQL5/Experts/Free Robots/MorningEvening StarDoji CCI.ex5
    48052  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BlackCrows WhiteSoldiers RSI.ex5
    25144  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Harami CCI.mq5
    47386  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BlackCrows WhiteSoldiers MFI.ex5
    23577  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BlackCrows WhiteSoldiers CCI.mq5
    26665  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/MorningEvening StarDoji Stoch.mq5
    23582  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BlackCrows WhiteSoldiers MFI.mq5
    47564  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Harami MFI.ex5
    25599  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Harami Stoch.mq5
    48848  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish MeetingLines Stoch.ex5
    23595  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish MeetingLines RSI.mq5
    24062  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BlackCrows WhiteSoldiers Stoch.mq5
    48772  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Engulfing Stoch.ex5
    48062  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Engulfing RSI.ex5
    25070  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Engulfing CCI.mq5
    25013  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/DarkCloud PiercingLine RSI.mq5
    49282  2026-06-21 22:59   MetaTrader 5/MQL5/Experts/Free Robots/MorningEvening StarDoji Stoch.ex5
    26197  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/MorningEvening StarDoji CCI.mq5
    25492  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/DarkCloud PiercingLine Stoch.mq5
    23595  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish MeetingLines CCI.mq5
    48960  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Harami CCI.ex5
    25012  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/DarkCloud PiercingLine MFI.mq5
    48264  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/DarkCloud PiercingLine MFI.ex5
    23595  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BlackCrows WhiteSoldiers RSI.mq5
    25084  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/HangingMan Hammer Stoch.mq5
    25559  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Engulfing Stoch.mq5
    48290  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BlackCrows WhiteSoldiers Stoch.ex5
    47820  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish MeetingLines CCI.ex5
    48656  2026-06-21 22:59   MetaTrader 5/MQL5/Experts/Free Robots/MorningEvening StarDoji RSI.ex5
    26192  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/MorningEvening StarDoji RSI.mq5
    47678  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Engulfing MFI.ex5
    25138  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Harami RSI.mq5
    48912  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish MeetingLines RSI.ex5
    24047  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish MeetingLines Stoch.mq5
    48324  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BlackCrows WhiteSoldiers CCI.ex5
    47836  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/HangingMan Hammer MFI.ex5
    48858  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/HangingMan Hammer Stoch.ex5
    49348  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Harami RSI.ex5
    48060  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Free Robots/BullishBearish Engulfing CCI.ex5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/
        0  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/MACD/
    46856  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/MACD/MACD Sample.ex5
    18514  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/MACD/MACD Sample.mq5
        0  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/Moving Average/
    36666  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/Moving Average/Moving Average.ex5
     8003  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Moving Average/Moving Average.mq5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Controls/
    17723  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Controls/ControlsDialog.mqh
   177326  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Controls/Controls.ex5
     2161  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Controls/Controls.mq5
        0  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/Correlation Matrix 3D/
    77294  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Correlation Matrix 3D/Correlation Matrix 3D.mq5
    69414  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/Correlation Matrix 3D/Correlation Matrix 3D.ex5
     8302  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Correlation Matrix 3D/Correlation Matrix 3D.mqproj
        0  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/Math 3D Morpher/
    35776  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D Morpher/Math 3D Morpher.mq5
    70620  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/Math 3D Morpher/Math 3D Morpher.ex5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D Morpher/Textures/
   196662  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D Morpher/Textures/checker.bmp
    16042  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D Morpher/Math 3D Morpher.mqproj
    13957  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D Morpher/Functions.mqh
        0  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/Math 3D/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/
      684  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/DoubleScrew.set
      684  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Granite.set
      696  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/ClimberDream.set
      686  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Sink.set
      688  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Hill.set
      692  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Hedgehog.set
      684  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Chomolungma.set
      684  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Screw.set
      684  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/MultyExtremalScrew.set
      686  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Skin.set
      686  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Trapfall.set
      688  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Sets/Josephine.set
    16958  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Math 3D.ico
     6986  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Math 3D.mq5
    41360  2026-06-21 22:47   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Math 3D.ex5
     6042  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Math 3D.mqproj
    16008  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/Math 3D/Functions.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/ChartInChart/
    30556  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/ChartInChart/ChartInChart.mq5
    20300  2026-06-21 22:46   MetaTrader 5/MQL5/Experts/Examples/ChartInChart/ChartInChart.ex5
    73399  2026-06-22 00:15   MetaTrader 5/MQL5/experts.dat
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Images/
     4152  2026-06-21 22:46   MetaTrader 5/MQL5/Images/dollar.bmp
     4152  2026-06-21 22:46   MetaTrader 5/MQL5/Images/euro.bmp
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/
    11473  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/NRTR Channel.mq5
    20370  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/Camarilla Channel.ex5
     9871  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/Keltner Channel.mq5
    15402  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/Parabolic Channel.ex5
    17314  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/Keltner Channel.ex5
    36396  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/MarketProfile Canvas.ex5
     8828  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/MarketProfile.mq5
     7589  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/Parabolic Channel.mq5
    11225  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/Fibonacci Channel.mq5
    10104  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/Woodie Channel.mq5
    11242  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/Pivot Channel.mq5
    18866  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/Pivot Channel.ex5
    14346  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/Donchian Channel.mq5
    19467  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/MarketProfile Canvas.mq5
    14592  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/Donchian Channel.ex5
    18142  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/NRTR Channel.ex5
     8529  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/DeMark Channel.mq5
    15173  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/MurreyMath Channel.mq5
    10647  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Free Indicators/Camarilla Channel.mq5
    20936  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/Fibonacci Channel.ex5
    19218  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/Woodie Channel.ex5
    19732  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/MarketProfile.ex5
    14958  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/DeMark Channel.ex5
    27062  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Free Indicators/MurreyMath Channel.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/
     6907  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Ultimate_Oscillator.mq5
    15456  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Custom Moving Average.ex5
     3236  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/TEMA.mq5
     7326  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Custom Moving Average.mq5
     3968  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/VROC.mq5
     3880  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ATR.mq5
     3059  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ColorBars.mq5
     4901  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/MACD.mq5
    10040  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Bears.ex5
     3693  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Bulls.mq5
     4876  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/MI.mq5
     4177  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/DeMarker.mq5
     9938  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Bulls.ex5
     8600  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/PVT.ex5
     8584  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/ColorLine.ex5
    11326  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/DEMA.ex5
    12172  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/MFI.ex5
     6064  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Alligator.mq5
    11614  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/DeMarker.ex5
    13462  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Ultimate_Oscillator.ex5
    17706  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/CHO.ex5
    16496  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Gator_2.ex5
    14050  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Envelopes.ex5
    13468  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/ADX.ex5
    16090  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/CHV.ex5
     4453  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/RSI.mq5
    10672  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/ATR.ex5
     3641  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/CCI.mq5
    14192  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/MACD.ex5
    15208  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/ADXW.ex5
     8490  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/WPR.mq5
     5356  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/CHO.mq5
     4440  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/CHV.mq5
     8788  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/AD.ex5
     3309  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/PVT.mq5
     6836  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ADXW.mq5
    14072  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/ZigzagColor.ex5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Panels/
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Panels/ChartPanel/
   136912  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Panels/ChartPanel/ChartPanel.ex5
    15250  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Panels/ChartPanel/PanelDialog.mqh
     2757  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Panels/ChartPanel/ChartPanel.mq5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Panels/SimplePanel/
     2757  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Panels/SimplePanel/SimplePanel.mq5
    14765  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Panels/SimplePanel/PanelDialog.mqh
   140520  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Panels/SimplePanel/SimplePanel.ex5
     4258  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/RVI.mq5
     4521  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Price_Channel.mq5
     8972  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Heiken_Ashi.ex5
    12790  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/ParabolicSAR.ex5
     2870  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Momentum.mq5
    15750  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/MI.ex5
     9877  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Gator_2.mq5
     5609  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ADX.mq5
     9606  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Fractals.ex5
    10880  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/VIDYA.ex5
     9570  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/Accelerator.ex5
     3733  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Heiken_Ashi.mq5
    11408  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/AMA.ex5
     3381  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/W_AD.mq5
     9350  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/Awesome_Oscillator.ex5
     8920  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/OBV.ex5
    18820  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ZigZag.mq5
     7056  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ParabolicSAR.mq5
     5020  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/BW-ZoneTrade.mq5
     9128  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/ASI.ex5
     5204  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Ichimoku.mq5
    14710  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/BB.ex5
    13268  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Force_Index.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Canvas/
     3577  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Canvas/FlameChart.mq5
    28034  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Canvas/FlameChart.ex5
     4129  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ASI.mq5
     5185  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/StdDev.mq5
    11062  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/ROC.ex5
     5817  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/BB.mq5
     8198  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/W_AD.ex5
    11252  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/WPR.ex5
    10247  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Gator.mq5
     8162  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/ColorBars.ex5
    10944  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Price_Channel.ex5
    12204  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/VROC.ex5
     2682  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ROC.mq5
    10908  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Momentum.ex5
    11584  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/TEMA.ex5
     3410  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/OBV.mq5
     5035  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/AMA.mq5
    12182  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/RSI.ex5
     3927  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Force_Index.mq5
     3688  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Bears.mq5
    16664  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Gator.ex5
     3368  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Volumes.mq5
    11312  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/CCI.ex5
    13564  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Ichimoku.ex5
    12266  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/RVI.ex5
     3375  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/AD.mq5
     9567  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ZigzagColor.mq5
    12344  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/TRIX.ex5
    10390  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/FrAMA.ex5
     9736  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/BW-ZoneTrade.ex5
     4996  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Stochastic.mq5
    10774  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/MarketFacilitationIndex.ex5
    14158  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/ZigZag.ex5
     5177  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/OsMA.mq5
    14084  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/StdDev.ex5
     5306  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Accelerator.mq5
     3343  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/TRIX.mq5
     4823  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/MFI.mq5
     3136  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ColorCandlesDaily.mq5
     3424  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Fractals.mq5
     2876  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/DPO.mq5
     5003  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/MarketFacilitationIndex.mq5
     4337  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Envelopes.mq5
    17320  2026-06-21 22:59   MetaTrader 5/MQL5/Indicators/Examples/Alligator.ex5
     5175  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/ColorLine.mq5
    12340  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Stochastic.ex5
    15280  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/OsMA.ex5
     3799  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/VIDYA.mq5
     3675  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/FrAMA.mq5
     4591  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/Awesome_Oscillator.mq5
     9286  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/Volumes.ex5
     9128  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/ColorCandlesDaily.ex5
     2940  2026-06-21 22:46   MetaTrader 5/MQL5/Indicators/Examples/DEMA.mq5
    12166  2026-06-21 23:00   MetaTrader 5/MQL5/Indicators/Examples/DPO.ex5
        0  2026-06-21 22:47   MetaTrader 5/MQL5/Profiles/
        0  2026-06-21 22:47   MetaTrader 5/MQL5/Profiles/Community/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/Tester/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/SymbolSets/
       64  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/SymbolSets/forex.major.set
      288  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/SymbolSets/forex.all.set
      218  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/SymbolSets/forex.crosses.set
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/Templates/
     4082  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Templates/ADX.tpl
     7214  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Templates/Momentum.tpl
     4866  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Templates/BollingerBands.tpl
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/Charts/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/Charts/British Pound/
     4434  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/British Pound/chart01.chr
     4434  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/British Pound/chart04.chr
      106  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/British Pound/order.wnd
     4432  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/British Pound/chart03.chr
     4432  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/British Pound/chart02.chr
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/Charts/Default/
     3506  2026-06-22 00:15   MetaTrader 5/MQL5/Profiles/Charts/Default/chart01.chr
     3818  2026-06-22 00:15   MetaTrader 5/MQL5/Profiles/Charts/Default/chart04.chr
      106  2026-06-22 00:15   MetaTrader 5/MQL5/Profiles/Charts/Default/order.wnd
     3986  2026-06-22 00:15   MetaTrader 5/MQL5/Profiles/Charts/Default/chart03.chr
     3524  2026-06-22 00:15   MetaTrader 5/MQL5/Profiles/Charts/Default/chart02.chr
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/Charts/Euro/
     4434  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Euro/chart01.chr
     4434  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Euro/chart04.chr
      106  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Euro/order.wnd
     4432  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Euro/chart03.chr
     4432  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Euro/chart02.chr
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/Charts/Market Overview/
     5652  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Market Overview/chart01.chr
     3168  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Market Overview/chart04.chr
      106  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Market Overview/order.wnd
     3022  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Market Overview/chart03.chr
     3166  2026-06-21 22:45   MetaTrader 5/MQL5/Profiles/Charts/Market Overview/chart02.chr
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Profiles/deleted/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/logs/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Libraries/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/
     6302  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestHashMap.mq5
    12001  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestRedBlackTree.mq5
    34226  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestArrayList.mq5
    62465  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestLinkedList.mq5
     6443  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestSortedMap.mq5
     8756  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestQueue.mq5
     8752  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestStack.mq5
     5426  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestSortedSet.mq5
     5013  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Generic/TestHashSet.mq5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Fuzzy/
    27020  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Fuzzy/TestFuzzy.mq5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Stat/
    58178  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Stat/TestStatBenchmark.mq5
    16162  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Stat/TestStatPrecision.mq5
   216091  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Stat/TestStat.mq5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Alglib/
    17911  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Alglib/TestInterfaces.mq5
    31148  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Alglib/TestClasses.mq5
   695999  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Alglib/TestInterfaces.mqh
  3105290  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/UnitTests/Alglib/TestClasses.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/SymbolInfo/
     8811  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/SymbolInfo/SymbolInfoSample.mq5
     1774  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/SymbolInfo/SymbolInfoSampleInit.mqh
    36830  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/SymbolInfo/SymbolInfoSample.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/AccountInfo/
     5904  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/AccountInfo/AccountInfoSample.mq5
      917  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/AccountInfo/AccountInfoSampleInit.mqh
    20716  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/AccountInfo/AccountInfoSample.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OrderInfo/
    27024  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OrderInfo/OrderInfoSample.ex5
      931  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OrderInfo/OrderInfoSampleInit.mqh
     7459  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OrderInfo/OrderInfoSample.mq5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/PositionInfo/
     7287  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/PositionInfo/PositionInfoSample.mq5
      830  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/PositionInfo/PositionInfoSampleInit.mqh
    22586  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/PositionInfo/PositionInfoSample.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/ObjectSphere/
     6030  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/ObjectSphere/SphereSample.mq5
    22138  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/ObjectSphere/SphereSample.ex5
     8030  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/ObjectSphere/Sphere.mqh
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/Canvas/
     6073  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Canvas/CanvasSample.mq5
    31610  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/Canvas/CanvasSample.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/Canvas/Charts/
    51050  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/Canvas/Charts/HistogramChartSample.ex5
    52162  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/Canvas/Charts/LineChartSample.ex5
     2172  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Canvas/Charts/LineChartSample.mq5
     3201  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Canvas/Charts/PieChartSample.mq5
    73214  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/Canvas/Charts/PieChartSample.ex5
     2205  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Canvas/Charts/HistogramChartSample.mq5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/ArrayDouble/
     4195  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/ArrayDouble/ArrayDoubleSample.mq5
    19530  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/ArrayDouble/ArrayDoubleSample.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/Remnant 3D/
     1744  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Remnant 3D/Remnant 3D.mqproj
    17186  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/Remnant 3D/Remnant 3D.ex5
     5696  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Remnant 3D/Remnant 3D.mq5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Remnant 3D/Shaders/
      254  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Remnant 3D/Shaders/vertex.hlsl
    10093  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/Remnant 3D/Shaders/pixel.hlsl
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/ObjectChart/
    25357  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/ObjectChart/ObjChartSample.mq5
     4182  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/ObjectChart/ChartSampleInit.mqh
    58110  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/ObjectChart/ObjChartSample.ex5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/
     7941  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/BitonicSort.mq5
     8654  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/MatrixMult.mq5
    15353  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/Wavelet.mq5
   110906  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/Wavelet.ex5
    21096  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/BitonicSort.ex5
    28684  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/FFT.ex5
    13394  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/FFT.mq5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/Kernels/
     2808  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/Kernels/matrixmult.cl
     1792  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/Kernels/wavelet.cl
     6038  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/Kernels/fft.cl
     1516  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/Kernels/bitonicsort.cl
    22046  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Double/MatrixMult.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/
     7718  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/BitonicSort.mq5
     8434  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/MatrixMult.mq5
    15753  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/Wavelet.mq5
   110474  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/Wavelet.ex5
    19958  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/BitonicSort.ex5
    29260  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/FFT.ex5
    13169  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/FFT.mq5
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/Kernels/
     2635  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/Kernels/matrixmult.cl
     1601  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/Kernels/wavelet.cl
     5862  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/Kernels/fft.cl
     1348  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/Kernels/bitonicsort.cl
    21440  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Float/MatrixMult.ex5
        0  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Seascape/
     8264  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Seascape/Seascape.cl
    15394  2026-06-21 23:00   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Seascape/Seascape.ex5
     6215  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Seascape/Seascape.mq5
     2486  2026-06-21 22:46   MetaTrader 5/MQL5/Scripts/Examples/OpenCL/Seascape/Seascape.mqproj
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Files/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Services/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/
     7249  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/HashFunction.mqh
     1253  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/DefaultComparer.mqh
     4695  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/ArrayFunction.mqh
     1457  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/DefaultEqualityComparer.mqh
     1103  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/EqualFunction.mqh
     8348  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/Introsort.mqh
     3601  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/PrimeGenerator.mqh
     7190  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Internal/CompareFunction.mqh
     8953  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Stack.mqh
    37086  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/HashSet.mqh
    25714  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/HashMap.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/
     2031  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/ISet.mqh
      998  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/IComparer.mqh
     1027  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/IEqualityComparer.mqh
     1391  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/IMap.mqh
     1352  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/IList.mqh
     1012  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/IEqualityComparable.mqh
     1142  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/ICollection.mqh
     1057  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Interfaces/IComparable.mqh
    29814  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/Queue.mqh
    25573  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/SortedSet.mqh
    50384  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/ArrayList.mqh
    14431  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/SortedMap.mqh
    21261  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/LinkedList.mqh
    74814  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Generic/RedBlackTree.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/
    69541  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/Trade.mqh
    20018  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/HistoryOrderInfo.mqh
    15820  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/PositionInfo.mqh
    22087  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/OrderInfo.mqh
    16313  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/DealInfo.mqh
    35851  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/SymbolInfo.mqh
    10730  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/TerminalInfo.mqh
    18130  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Trade/AccountInfo.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/
    23807  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsArrows.mqh
     8273  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectPanel.mqh
    17095  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsGann.mqh
    17330  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectSubChart.mqh
    11883  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsChannels.mqh
    41365  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObject.mqh
     9567  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsElliott.mqh
    17506  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsFibo.mqh
    15506  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsLines.mqh
     7288  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsShapes.mqh
    38305  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsTxtControls.mqh
    21277  2026-06-21 22:46   MetaTrader 5/MQL5/Include/ChartObjects/ChartObjectsBmpControls.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Trailing/
     5527  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Trailing/TrailingParabolicSAR.mqh
     5639  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Trailing/TrailingFixedPips.mqh
     2139  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Trailing/TrailingNone.mqh
     6725  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Trailing/TrailingMA.mqh
    20246  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/ExpertSignal.mqh
     6502  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/ExpertTrade.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Money/
     3531  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Money/MoneyFixedLot.mqh
     6231  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Money/MoneySizeOptimized.mqh
     4454  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Money/MoneyFixedRisk.mqh
     3619  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Money/MoneyFixedMargin.mqh
     3356  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Money/MoneyNone.mqh
   122604  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Expert.mqh
     4963  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/ExpertMoney.mqh
     1738  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/ExpertTrailing.mqh
    27603  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/ExpertBase.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/
    20197  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalStoch.mqh
    12007  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalMA.mqh
     9652  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalEnvelopes.mqh
    12351  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalAMA.mqh
    11971  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalBearsPower.mqh
    11764  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalFrAMA.mqh
     7678  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalAC.mqh
    11738  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalDEMA.mqh
    18757  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalRSI.mqh
    13681  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalAO.mqh
     8156  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalRVI.mqh
    11979  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalBullsPower.mqh
    11732  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalTEMA.mqh
    17541  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalCCI.mqh
    18103  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalTRIX.mqh
     7834  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalSAR.mqh
    17303  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalDeMarker.mqh
     4646  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalITF.mqh
    16579  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalWPR.mqh
    19863  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Expert/Signal/SignalMACD.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Graphics/
    12581  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Graphics/Axis.mqh
   173126  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Graphics/Graphic.mqh
     3120  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Graphics/ColorGenerator.mqh
    22801  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Graphics/Curve.mqh
      683  2026-06-21 22:46   MetaTrader 5/MQL5/Include/StdLibErr.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/
    34652  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/Canvas3D.mqh
    27042  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/FlameCanvas.mqh
   156459  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/Canvas.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/
     4968  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXInput.mqh
    15738  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXMesh.mqh
     6405  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXSurface.mqh
     3208  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXBox.mqh
     1744  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXObject.mqh
    13160  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXDispatcher.mqh
     2106  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXObjectBase.mqh
     8568  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXHandle.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/Shaders/
     3307  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/Shaders/DefaultShaderPixel.hlsl
     2805  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/Shaders/DefaultShaderVertex.hlsl
     4048  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXData.mqh
     4354  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXBuffers.mqh
   155150  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXMath.mqh
     6890  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXTexture.mqh
    36695  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXUtils.mqh
    16984  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/DX/DXShader.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/Charts/
    13713  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/Charts/PieChart.mqh
    12605  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/Charts/LineChart.mqh
    11932  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/Charts/HistogramChart.mqh
    36139  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Canvas/Charts/ChartCanvas.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/
    19825  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/Indicator.mqh
    12252  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/Indicators.mqh
    73859  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/Oscilators.mqh
    33009  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/BillWilliams.mqh
    12629  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/Series.mqh
    17740  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/Volumes.mqh
    73766  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/Trend.mqh
    63360  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/TimeSeries.mqh
     8168  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Indicators/Custom.mqh
    10737  2026-06-21 22:46   MetaTrader 5/MQL5/Include/MovingAverages.mqh
     5755  2026-06-21 22:46   MetaTrader 5/MQL5/Include/VirtualKeys.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/
    25009  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayUShort.mqh
    25319  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayObj.mqh
    24826  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayChar.mqh
    24776  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayLong.mqh
    24704  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayInt.mqh
    24865  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayULong.mqh
    25433  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayDouble.mqh
    24841  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayColor.mqh
    25358  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayFloat.mqh
    21080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/List.mqh
    25106  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayString.mqh
    24792  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayUInt.mqh
    24915  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayUChar.mqh
     6965  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/Array.mqh
    25106  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayDatetime.mqh
     6801  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/TreeNode.mqh
    24921  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/ArrayShort.mqh
    14241  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Arrays/Tree.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/
    10629  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/WndObj.mqh
    14144  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/CheckGroup.mqh
    15174  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/DateDropList.mqh
    13397  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/ComboBox.mqh
    10338  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/SpinEdit.mqh
     5871  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Panel.mqh
    10702  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/DatePicker.mqh
    30356  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Wnd.mqh
    11453  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/BmpButton.mqh
     7677  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/CheckBox.mqh
     6892  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Button.mqh
    26735  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Scrolls.mqh
    16382  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/WndContainer.mqh
    11086  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Rect.mqh
     6989  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/RadioButton.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/
      632  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/RadioButtonOff.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/Restore.bmp
      632  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/RadioButtonOn.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/Turn.bmp
      568  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/SpinInc.bmp
     1144  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/ThumbHor.bmp
      824  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/Down.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/RightTransp.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/DropOn.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/UpTransp.bmp
      824  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/Up.bmp
      824  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/Right.bmp
     2104  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/DateDropOn.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/DropOff.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/LeftTransp.bmp
      824  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/Left.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/DownTransp.bmp
     1112  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/ThumbVert.bmp
     2104  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/DateDropOff.bmp
      576  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/CheckBoxOff.bmp
      568  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/SpinDec.bmp
      576  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/CheckBoxOn.bmp
     1080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/res/Close.bmp
    38884  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Dialog.mqh
    20099  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/ListView.mqh
     4309  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Label.mqh
    12589  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Defines.mqh
     5602  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Picture.mqh
     8938  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/Edit.mqh
    13558  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/RadioGroup.mqh
    12237  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Controls/WndClient.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/
    12170  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/genericfuzzysystem.mqh
    44306  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/membershipfunction.mqh
     9060  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/dictionary.mqh
    23075  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/mamdanifuzzysystem.mqh
    13323  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/sugenofuzzysystem.mqh
    18196  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/fuzzyrule.mqh
    37389  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/ruleparser.mqh
     7352  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/helper.mqh
     5586  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/fuzzyvariable.mqh
     3819  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/fuzzyterm.mqh
     7238  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/inferencemethod.mqh
    11248  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Fuzzy/sugenovariable.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/
    28548  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/T.mqh
    25659  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Uniform.mqh
    29634  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/NegativeBinomial.mqh
    24774  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Exponential.mqh
     1139  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Stat.mqh
    40671  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Normal.mqh
    29245  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Lognormal.mqh
    33321  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Beta.mqh
    47734  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/NoncentralT.mqh
    32547  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Poisson.mqh
    27532  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Weibull.mqh
    37497  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/NoncentralChiSquare.mqh
    35728  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Binomial.mqh
   434790  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Math.mqh
    32373  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Gamma.mqh
    25520  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Cauchy.mqh
    24891  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/ChiSquare.mqh
    41195  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/NoncentralBeta.mqh
    27860  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Logistic.mqh
    25490  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Geometric.mqh
    27612  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/F.mqh
    35826  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/NoncentralF.mqh
    35334  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Stat/Hypergeometric.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/
    13809  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/bitconvert.mqh
   417177  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/statistics.mqh
    46475  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/matrix.mqh
  1490029  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/linalg.mqh
   241208  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/specialfunctions.mqh
    94444  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/fasttransforms.mqh
    21765  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/delegatefunctions.mqh
  1151833  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/dataanalysis.mqh
    92144  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/ap.mqh
   122283  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/alglibmisc.mqh
  2300652  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/optimization.mqh
    33183  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/diffequations.mqh
   593648  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/alglibinternal.mqh
  2478270  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/alglib.mqh
   302159  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/solvers.mqh
     4080  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/arrayresize.mqh
   119413  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/integration.mqh
  1465208  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Math/Alglib/interpolation.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Files/
    12882  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Files/FilePipe.mqh
     2825  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Files/FileTxt.mqh
    12206  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Files/File.mqh
    20944  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Files/FileBin.mqh
     6995  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Files/FileBMP.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Tools/
    17883  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Tools/DateTime.mqh
     2036  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Object.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/OpenCL/
    28662  2026-06-21 22:46   MetaTrader 5/MQL5/Include/OpenCL/OpenCL.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Charts/
    63640  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Charts/Chart.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Strings/
    13847  2026-06-21 22:46   MetaTrader 5/MQL5/Include/Strings/String.mqh
        0  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/
    44329  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/winbase.mqh
     2952  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/libloaderapi.mqh
     9487  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/fileapi.mqh
     1589  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/processenv.mqh
     5838  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/memoryapi.mqh
    16588  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/securitybaseapi.mqh
    10250  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/processthreadsapi.mqh
      827  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/winapi.mqh
     1165  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/handleapi.mqh
     1933  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/errhandlingapi.mqh
    82945  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/winuser.mqh
    97680  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/winnt.mqh
     6133  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/winreg.mqh
     4827  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/sysinfoapi.mqh
     8839  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/windef.mqh
    64995  2026-06-21 22:46   MetaTrader 5/MQL5/Include/WinAPI/wingdi.mqh
 23312560  2026-06-21 22:40   MetaTrader 5/uninstall.exe
109082688  2026-06-21 22:45   MetaTrader 5/MetaEditor64.exe
/tmp/derivchk/MetaTrader 5/config/servers.dat
softverse@Softverse:/tmp/derivchk$