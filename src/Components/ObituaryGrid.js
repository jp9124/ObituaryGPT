import ObituaryCard from './ObituaryCard';

function ObituaryGrid({ obituaries, expandedId, onToggleObituary }) {
  return (
    <section className="obituary-grid" aria-label="Obituaries">
      {obituaries.map((person) => {
        const isExpanded = expandedId === person.id;

        return (
          <ObituaryCard
            key={person.id}
            person={person}
            isExpanded={isExpanded}
            onToggle={() => onToggleObituary(isExpanded ? null : person.id)}
          />
        );
      })}
    </section>
  );
}

export default ObituaryGrid;
