import { useEffect, useState } from 'react';
import Header from './Components/Header';
import NewObituaryModal from './Components/NewObituaryModal';
import ObituaryGrid from './Components/ObituaryGrid';
import { normalizeObituary } from './utils/obituaries';

const GET_OBITUARIES_URL = process.env.REACT_APP_GET_OBITUARIES_URL;
const CREATE_OBITUARY_URL = process.env.REACT_APP_CREATE_OBITUARY_URL;

function App() {
  const [obituaries, setObituaries] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  useEffect(() => {
    if (!GET_OBITUARIES_URL) return;

    const loadObituaries = async () => {
      try {
        const response = await fetch(GET_OBITUARIES_URL);
        if (!response.ok) throw new Error('Could not load obituaries');

        const data = await response.json();
        const items = Array.isArray(data) ? data : data.obituaries || data.items || [];

        setObituaries(items.map(normalizeObituary));
      } catch (error) {
        console.warn(error);
        setFormError('Could not load saved obituaries. Check the GET Lambda URL.');
      }
    };

    loadObituaries();
  }, []);

  const createLocalObituary = (form, pictureUrl) => ({
    id: window.crypto?.randomUUID?.() || `${form.name}-${Date.now()}`,
    name: form.name,
    born: form.born,
    died: form.died,
    picture: pictureUrl,
    obituary: `${form.name} lived a life worthy of a final standing ovation. Their story began in ${new Date(
      `${form.born}T00:00:00`
    ).getFullYear()} and continued with moments of courage, tenderness, and unforgettable presence until ${new Date(
      `${form.died}T00:00:00`
    ).getFullYear()}.`,
  });

  const submitObituary = async (form) => {
    if (!form.name || !form.born || !form.died || !form.picture) return;

    setIsSubmitting(true);
    setFormError('');
    const previewUrl = URL.createObjectURL(form.picture);

    try {
      if (CREATE_OBITUARY_URL) {
        const body = new FormData();
        body.append('name', form.name);
        body.append('born', form.born);
        body.append('died', form.died);
        body.append('picture', form.picture);

        const response = await fetch(CREATE_OBITUARY_URL, {
          method: 'POST',
          body,
        });

        if (!response.ok) {
          let message = 'Could not create obituary';
          try {
            const details = await response.json();
            message = details.message || message;
          } catch (parseError) {
            console.warn(parseError);
          }
          throw new Error(message);
        }

        const created = normalizeObituary(await response.json(), 0);
        setObituaries((current) => [created, ...current]);
      } else {
        setObituaries((current) => [createLocalObituary(form, previewUrl), ...current]);
      }

      setIsModalOpen(false);
    } catch (error) {
      console.warn(error);
      if (CREATE_OBITUARY_URL) {
        setFormError(error.message || 'Could not create obituary');
      } else {
        setObituaries((current) => [createLocalObituary(form, previewUrl), ...current]);
        setIsModalOpen(false);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="app-shell">
      <Header onOpenModal={() => setIsModalOpen(true)} />

      <ObituaryGrid
        obituaries={obituaries}
        expandedId={expandedId}
        onToggleObituary={setExpandedId}
      />

      {isModalOpen && (
        <NewObituaryModal
          error={formError}
          isSubmitting={isSubmitting}
          onClose={() => {
            setFormError('');
            setIsModalOpen(false);
          }}
          onSubmit={submitObituary}
        />
      )}
    </main>
  );
}

export default App;
