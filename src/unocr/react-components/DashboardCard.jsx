import React from 'react';
import PropTypes from 'prop-types';

/* ═╁▸ DashboardCard ═══════════════════════════════════════════════════════════
   Card de statistiques réutilisable pour le dashboard UniOCR.
   Affiche un chiffre clé avec un label, une sous-label et un petit graphique
   ou icône de tendance.
═╁══════════════════════════════════════════════════════════════════════════════════════════════════════ */

const DashboardCard = ({ title, value, subtitle, trend, trendColor, className }) => {
  const renderTrend = () => {
    if (!trend) return null;

    return (
      <div className="dashboard-card-trend" style={{ color: trendColor }}>
        {trend}
      </div>
    );
  };

  return (
    <div className={`dashboard-card ${className || ''}`}>
      <div className="dashboard-card-value">{value}</div>
      <div className="dashboard-card-title">{title}</div>
      <div className="dashboard-card-subtitle">{subtitle || ''}</div>
      {renderTrend()}
    </div>
  );
};

/* PropTypes */
DashboardCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  subtitle: PropTypes.string,
  trend: PropTypes.string,
  trendColor: PropTypes.string,
  className: PropTypes.string,
};

DashboardCard.defaultProps = {
  subtitle: '',
  trend: null,
  trendColor: '#27ae60',
  className: '',
};

/* ╁═══════════════════════════════════════════════════════════════════════════════════════════════════════ */

export default DashboardCard;