import React from 'react';
import DashboardCard from './DashboardCard';

/* ═╁▸ StatsOverview ═╁════════════════════════════════════════════════════════════
   Section de statistiques globales affichant les indicateurs clés.
═╁════════════════════════════════════════════════════════════════════════════════════════════════════════ */

const StatsOverview = ({ stats }) => {
  const renderStats = () => {
    if (!stats || !stats.total_jobs) return null;

    return (
      <div className="stats-overview-grid">
        <DashboardCard
          title="Documents totaux"
          value={stats.total_jobs}
          subtitle="Traités avec UniOCR"
          trend={`${stats.taux_reussite}% succès`}
          trendColor="#27ae60"
        />
        <DashboardCard
          title="En cours"
          value={stats.repartition_par_statut.en_cours}
          subtitle="En traitement"
          trend={`${stats.repartition_par_statut.en_attente} en file`}
          trendColor="#f39c12"
        />
        <DashboardCard
          title="Erreurs"
          value={stats.repartition_par_statut.erreur}
          subtitle="Traitement échoué"
          trendColor="#e74c3c"
        />
        <DashboardCard
          title="En attente"
          value={stats.repartition_par_statut.en_attente}
          subtitle="En file d'attente"
          trendColor="#3498db"
        />
      </div>
    );
  };

  return <div className="stats-overview-container">{renderStats()}</div>;
};

StatsOverview.propTypes = {
  stats: PropTypes.shape({
    total_jobs: PropTypes.number.isRequired,
    taux_reussite: PropTypes.number.isRequired,
    repartition_par_statut: PropTypes.shape({
      en_cours: PropTypes.number.isRequired,
      en_attente: PropTypes.number.isRequired,
      erreur: PropTypes.number.isRequired,
    }).isRequired,
  }).isRequired,
};

StatsOverview.defaultProps = {};

export default StatsOverview;