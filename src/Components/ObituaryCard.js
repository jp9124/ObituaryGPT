import { formatDate } from '../utils/date';
import AudioPlayButton from './AudioPlayButton';

function ObituaryCard({ person, isExpanded, onToggle }) {
  return (
    <article className="obituary-card">
      <img src={person.picture} alt={person.name} />
      <div className="card-copy">
        <h2>{person.name}</h2>
        <p>
          {formatDate(person.born)} - {formatDate(person.died)}
        </p>
        <button
          className={`expand-button ${isExpanded ? 'is-open' : ''}`}
          onClick={onToggle}
          aria-label={`${isExpanded ? 'Hide' : 'Show'} ${person.name} obituary`}
          aria-expanded={isExpanded}
        >
          ▼
        </button>
        {isExpanded && (
          <div className="obituary-details">
            <p>{person.obituary}</p>
            <AudioPlayButton audioUrl={person.audio} />
          </div>
        )}
      </div>
    </article>
  );
}

export default ObituaryCard;
