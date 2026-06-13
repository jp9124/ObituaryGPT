export const normalizeObituary = (item, index) => ({
  id: item.id || item.obituary_id || `${item.name}-${index}`,
  name: item.name || 'Unknown',
  born: item.born || item.birthDate || item.dateOfBirth || item.date_of_birth,
  died: item.died || item.deathDate || item.dateOfDeath || item.date_of_death,
  picture: item.picture || item.image || item.picture_url || item.imageUrl,
  obituary: item.obituary || item.text || item.body || '',
  audio: item.audio || item.audio_url || item.speech_url || '',
});
