"use client";

/**
 * Local prop shape: only the fields actually rendered by the card.
 * Decoupled from the heavier `@/lib/schemas` `Asset` interface so callers
 * (e.g. `Portfolio.tsx`) can pass simpler API payloads without satisfying
 * every server-side column.
 */
interface PortfolioCardAsset {
  ticker: string;
  name: string;
  current_price?: number;
  buffett_score?: number;
  confidence_score?: number;
  target_price?: number;
  stop_loss?: number;
  kelly_position_size?: number;
  logo_url?: string;
  avanza_url?: string;
  nordnet_url?: string;
  unrealized_pnl_percentage?: number;
}

interface PortfolioCardProps {
  asset: PortfolioCardAsset;
  onClick?: () => void;
}

export default function PortfolioCard({ asset, onClick }: PortfolioCardProps) {
  const {
    ticker,
    name,
    current_price,
    buffett_score,
    confidence_score,
    target_price,
    stop_loss,
    kelly_position_size,
    logo_url,
    avanza_url,
    nordnet_url,
    unrealized_pnl_percentage,
  } = asset;

  const getRecommendationColor = (score: number) => {
    if (score >= 0.80) return "text-positive";
    if (score >= 0.60) return "text-positive";
    if (score >= 0.40) return "text-primary";
    if (score >= 0.20) return "text-negative";
    return "text-negative";
  };

  const getRecommendationText = (score: number) => {
    if (score >= 0.80) return "STRONG BUY";
    if (score >= 0.60) return "BUY";
    if (score >= 0.40) return "HOLD";
    if (score >= 0.20) return "SELL";
    return "STRONG SELL";
  };

  const pnlColor = unrealized_pnl_percentage
    ? unrealized_pnl_percentage >= 0
      ? "text-positive"
      : "text-negative"
    : "text-primary";

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer border border-gray-200"
    >
      {/* Header with logo and ticker */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          {logo_url && (
            <img
              src={logo_url}
              alt={`${ticker} logo`}
              className="w-12 h-12 rounded-full object-cover"
            />
          )}
          <div>
            <h3 className="text-xl font-bold text-primary">{ticker}</h3>
            <p className="text-sm text-gray-600">{name}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-primary">
            {current_price ? `${current_price.toFixed(2)} SEK` : "N/A"}
          </p>
          {unrealized_pnl_percentage !== null && unrealized_pnl_percentage !== undefined && (
            <p className={`text-sm font-semibold ${pnlColor}`}>
              {unrealized_pnl_percentage >= 0 ? "+" : ""}
              {unrealized_pnl_percentage.toFixed(2)}%
            </p>
          )}
        </div>
      </div>

      {/* Buffett Score */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-semibold text-primary">Buffett Score</span>
          <span className={`text-lg font-bold ${getRecommendationColor(buffett_score || 0)}`}>
            {buffett_score ? (buffett_score * 100).toFixed(0) : "N/A"}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-positive h-2 rounded-full transition-all"
            style={{ width: `${(buffett_score || 0) * 100}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className={`text-xs font-semibold ${getRecommendationColor(buffett_score || 0)}`}>
            {getRecommendationText(buffett_score || 0)}
          </span>
          <span className="text-xs text-gray-500">
            Confidence: {confidence_score ? (confidence_score * 100).toFixed(0) : "N/A"}%
          </span>
        </div>
      </div>

      {/* Risk Management */}
      {(target_price || stop_loss) && (
        <div className="mb-4 grid grid-cols-2 gap-3">
          {target_price && (
            <div className="bg-green-50 rounded p-2">
              <p className="text-xs text-gray-600">Target</p>
              <p className="text-sm font-semibold text-positive">
                {target_price.toFixed(2)} SEK
              </p>
            </div>
          )}
          {stop_loss && (
            <div className="bg-red-50 rounded p-2">
              <p className="text-xs text-gray-600">Stop Loss</p>
              <p className="text-sm font-semibold text-negative">
                {stop_loss.toFixed(2)} SEK
              </p>
            </div>
          )}
        </div>
      )}

      {/* Kelly Position Size */}
      {kelly_position_size !== undefined && kelly_position_size !== null && (
        <div className="mb-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Recommended Position</span>
            <span className="text-sm font-semibold text-primary">
              {(kelly_position_size * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      )}

      {/* Deep Links */}
      <div className="flex space-x-2 mt-4 pt-4 border-t border-gray-200">
        {avanza_url && (
          <a
            href={avanza_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-blue-600 text-white text-center py-2 rounded text-sm font-semibold hover:bg-blue-700 transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            Avanza
          </a>
        )}
        {nordnet_url && (
          <a
            href={nordnet_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-gray-800 text-white text-center py-2 rounded text-sm font-semibold hover:bg-gray-900 transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            Nordnet
          </a>
        )}
      </div>
    </div>
  );
}
