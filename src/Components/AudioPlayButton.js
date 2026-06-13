import { useRef, useState } from 'react';

function AudioPlayButton({ audioUrl }) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const toggleAudio = async () => {
    if (!audioRef.current || !audioUrl) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    await audioRef.current.play();
    setIsPlaying(true);
  };

  return (
    <div className="audio-action">
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onEnded={() => setIsPlaying(false)}
          onPause={() => setIsPlaying(false)}
        >
          Your browser does not support audio playback.
        </audio>
      )}
      <button
        type="button"
        className={`audio-play-button ${isPlaying ? 'is-playing' : ''}`}
        onClick={toggleAudio}
        disabled={!audioUrl}
        aria-label={audioUrl ? `${isPlaying ? 'Pause' : 'Play'} obituary audio` : 'Audio unavailable'}
        title={audioUrl ? 'Play obituary audio' : 'Audio appears after Polly creates an obituary'}
      >
        <span aria-hidden="true" />
      </button>
      {!audioUrl && <p className="audio-unavailable">Audio appears for generated obituaries.</p>}
    </div>
  );
}

export default AudioPlayButton;
