import { useState } from 'react';

const emptyForm = {
  name: '',
  born: '',
  died: '',
  picture: null,
};

function NewObituaryModal({ error, isSubmitting, onClose, onSubmit }) {
  const [form, setForm] = useState(emptyForm);

  const updateField = (event) => {
    const { name, value, files } = event.target;
    setForm((current) => ({
      ...current,
      [name]: files ? files[0] : value,
    }));
  };

  const closeModal = () => {
    if (!isSubmitting) onClose();
  };

  const submitForm = async (event) => {
    event.preventDefault();
    await onSubmit(form);
    setForm(emptyForm);
  };

  return (
    <div className="modal-backdrop" onMouseDown={closeModal}>
      <form
        className="obituary-modal"
        onSubmit={submitForm}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="close-button"
          onClick={closeModal}
          aria-label="Close create obituary form"
        >
          x
        </button>
        <h2>Create a New Obituary</h2>
        <div
          className="floral-underline"
          style={{ backgroundImage: `url(${process.env.PUBLIC_URL}/floral-underline.png)` }}
          aria-hidden="true"
        />
        {error && <p className="form-error">{error}</p>}

        <label>
          <span>Name:</span>
          <input
            name="name"
            type="text"
            placeholder="Ex. King Mufasa"
            value={form.name}
            onChange={updateField}
            required
          />
        </label>

        <label className="file-row">
          <span>Picture:</span>
          <input
            name="picture"
            type="file"
            accept="image/*"
            onChange={updateField}
            required
          />
        </label>

        <label>
          <span>Date of Birth:</span>
          <input
            name="born"
            type="date"
            value={form.born}
            onChange={updateField}
            required
          />
        </label>

        <label>
          <span>Date of Death:</span>
          <input
            name="died"
            type="date"
            value={form.died}
            onChange={updateField}
            required
          />
        </label>

        <button className="generate-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Generating...' : 'Generate Obituary'}
        </button>
      </form>
    </div>
  );
}

export default NewObituaryModal;
