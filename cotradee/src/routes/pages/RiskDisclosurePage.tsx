import { Link } from 'react-router-dom';
import LegalPageLayout from '@/features/legal/LegalPageLayout';
import '@/features/legal/legal.css';

const SECTIONS = [
  { id: 'overview', title: '1. Overview' },
  { id: 'trading-risk', title: '2. Trading Risk' },
  { id: 'leverage-risk', title: '3. Leverage Risk' },
  { id: 'automation-risk', title: '4. Automation Risk' },
  { id: 'ai-limitations', title: '5. AI Limitations' },
  { id: 'market-risk', title: '6. Market Risk' },
  { id: 'broker-risk', title: '7. Broker Risk' },
  { id: 'no-guarantees', title: '8. No Guarantees' },
  { id: 'acknowledgement', title: '9. Acknowledgement' },
  { id: 'contact', title: '10. Contact' },
];

export default function RiskDisclosurePage() {
  return (
    <LegalPageLayout
      title="Risk Disclosure"
      subtitle="This disclosure outlines the material risks associated with using the Exoper platform and engaging in financial trading. Read this carefully before using any feature of the Platform."
      effectiveDate="1 January 2026"
      lastUpdated="1 January 2026"
      sections={SECTIONS}
    >
      {/* 1. Overview */}
      <h2 id="overview">1. Overview</h2>
      <div className="legal-warning">
        <p>
          <strong>Trading financial instruments involves substantial risk of loss and is
          not suitable for all investors. You may lose some or all of your invested capital.
          Do not trade with money you cannot afford to lose.</strong>
        </p>
      </div>
      <p>
        Exoper provides structured trading infrastructure, AI-assisted analysis, and
        automated execution tooling. The Platform is designed to support disciplined
        decision-making — it does not eliminate trading risk. This Risk Disclosure
        describes the principal risks you should understand before using the Platform.
      </p>
      <p>
        This disclosure does not constitute financial advice. If you are uncertain about
        the suitability of trading for your circumstances, you should seek independent
        professional advice.
      </p>

      {/* 2. Trading Risk */}
      <h2 id="trading-risk">2. General Trading Risk</h2>
      <p>
        Financial markets are inherently unpredictable. Trading in foreign exchange (forex),
        commodities, indices, and other instruments carries significant risk, including:
      </p>
      <ul>
        <li><strong>Capital loss:</strong> You can lose the entire amount you invest in a trade</li>
        <li><strong>Volatility:</strong> Prices can move rapidly and unpredictably, especially around economic events</li>
        <li><strong>Liquidity risk:</strong> In certain market conditions, it may be difficult to exit positions at desired prices</li>
        <li><strong>Gap risk:</strong> Markets can open significantly higher or lower than the previous close, bypassing stop-loss orders</li>
        <li><strong>Counterparty risk:</strong> Your broker may fail to execute orders as expected</li>
      </ul>
      <p>
        Past performance of any trading strategy, system, or analysis output is not
        indicative of future results.
      </p>

      {/* 3. Leverage Risk */}
      <h2 id="leverage-risk">3. Leverage &amp; Margin Risk</h2>
      <p>
        Many financial instruments traded via MT5 and similar platforms involve leverage.
        Leverage amplifies both potential gains and potential losses:
      </p>
      <ul>
        <li>A small adverse price movement can result in a loss greater than your initial deposit</li>
        <li>Margin calls may require you to deposit additional funds or have positions closed automatically</li>
        <li>High leverage increases the speed at which losses can accumulate</li>
      </ul>
      <p>
        Exoper&rsquo;s risk management features (daily loss limits, drawdown controls,
        position sizing) are designed to help manage leverage risk, but they do not
        eliminate it. You are responsible for configuring these parameters appropriately
        for your risk tolerance.
      </p>

      {/* 4. Automation Risk */}
      <h2 id="automation-risk">4. Automated Execution Risk</h2>
      <p>
        The Platform supports automated trade execution. Automated systems carry specific
        risks that differ from manual trading:
      </p>
      <ul>
        <li><strong>System failure:</strong> Software bugs, network interruptions, or infrastructure outages may prevent orders from being placed or cancelled</li>
        <li><strong>Execution delay:</strong> There may be latency between signal generation and order placement, resulting in different fill prices than expected</li>
        <li><strong>Misconfiguration:</strong> Incorrect risk settings, position sizing parameters, or execution modes can result in unintended trading behaviour</li>
        <li><strong>Runaway automation:</strong> In rare circumstances, automated systems may behave unexpectedly if market conditions fall outside the parameters they were designed for</li>
        <li><strong>Broker API failures:</strong> Your broker&rsquo;s API may be unavailable, causing execution failures</li>
      </ul>
      <p>
        You are responsible for monitoring your automated configurations. You should
        regularly review active positions, execution logs, and system status. You should
        disable automation if you observe unexpected behaviour.
      </p>

      {/* 5. AI Limitations */}
      <h2 id="ai-limitations">5. AI Analysis Limitations</h2>
      <p>
        Exoper uses large language models (LLMs) and retrieval-augmented generation (RAG)
        to produce trading analysis. You must understand the following limitations:
      </p>
      <ul>
        <li><strong>Probabilistic outputs:</strong> AI analysis is probabilistic, not deterministic. The same market conditions may produce different outputs on different runs.</li>
        <li><strong>Hallucination risk:</strong> AI models can produce plausible-sounding but incorrect analysis. The RAG layer mitigates this by grounding reasoning in institutional rules, but it does not eliminate it.</li>
        <li><strong>Historical bias:</strong> AI models are trained on historical data and may not adapt quickly to novel market regimes or unprecedented events.</li>
        <li><strong>Retrieval limitations:</strong> The quality of analysis depends on the relevance of retrieved knowledge. Unusual market conditions may not be well-represented in the knowledge base.</li>
        <li><strong>No guarantee of accuracy:</strong> Confidence scores and grades are internal metrics, not guarantees of trade success.</li>
      </ul>
      <p>
        AI analysis outputs should be treated as one input into your decision-making
        process, not as definitive trading instructions.
      </p>

      {/* 6. Market Risk */}
      <h2 id="market-risk">6. Market &amp; Macro Risk</h2>
      <p>
        Financial markets are affected by a wide range of factors outside any system&rsquo;s
        ability to predict or control:
      </p>
      <ul>
        <li>Central bank policy decisions and interest rate changes</li>
        <li>Geopolitical events, conflicts, and sanctions</li>
        <li>Economic data releases (NFP, CPI, GDP, etc.)</li>
        <li>Regulatory changes affecting financial markets</li>
        <li>Black swan events and force majeure circumstances</li>
        <li>Market manipulation by large institutional participants</li>
      </ul>
      <p>
        The Platform&rsquo;s macro analysis layer monitors many of these factors, but
        cannot predict all market-moving events. You should always be aware of the
        economic calendar and major upcoming events when running automated strategies.
      </p>

      {/* 7. Broker Risk */}
      <h2 id="broker-risk">7. Broker &amp; Counterparty Risk</h2>
      <p>
        Exoper connects to your broker account but does not act as a broker. Risks
        associated with your broker include:
      </p>
      <ul>
        <li>Broker insolvency or regulatory action</li>
        <li>Requotes, slippage, and execution quality variations</li>
        <li>Broker-imposed trading restrictions or account suspensions</li>
        <li>Differences between demo and live account execution</li>
        <li>Spread widening during high-volatility periods</li>
      </ul>
      <p>
        You are responsible for selecting a reputable, regulated broker. Exoper is not
        responsible for your broker&rsquo;s actions, failures, or execution quality.
      </p>

      {/* 8. No Guarantees */}
      <h2 id="no-guarantees">8. No Profit Guarantees</h2>
      <div className="legal-callout">
        <p>
          <strong>Exoper makes no representation, warranty, or guarantee that use of the
          Platform will result in profitable trading. No analysis output, signal, grade,
          or confidence score constitutes a guarantee of profit or a promise of positive
          returns.</strong>
        </p>
      </div>
      <p>
        The Platform is designed to improve decision quality and enforce trading discipline.
        It cannot guarantee outcomes because:
      </p>
      <ul>
        <li>Markets are inherently uncertain and unpredictable</li>
        <li>Even high-quality setups can result in losses</li>
        <li>Execution quality depends on factors outside our control</li>
        <li>Your risk configuration directly affects your outcomes</li>
      </ul>

      {/* 9. Acknowledgement */}
      <h2 id="acknowledgement">9. Acknowledgement</h2>
      <p>
        By using the Platform, you acknowledge that:
      </p>
      <ul>
        <li>You have read and understood this Risk Disclosure in full</li>
        <li>You understand that trading involves substantial risk of loss</li>
        <li>You are trading with capital you can afford to lose</li>
        <li>You are not relying on Exoper for financial advice</li>
        <li>You accept full responsibility for your trading decisions and their outcomes</li>
        <li>You will monitor your automated configurations and take responsibility for their behaviour</li>
      </ul>

      {/* 10. Contact */}
      <h2 id="contact">10. Contact</h2>
      <p>
        If you have questions about this Risk Disclosure:
      </p>
      <ul>
        <li>Email: <a href="mailto:legal@exoper.com">legal@exoper.com</a></li>
        <li>Support: <Link to="/dashboard/support">Platform Support Centre</Link></li>
      </ul>
    </LegalPageLayout>
  );
}
