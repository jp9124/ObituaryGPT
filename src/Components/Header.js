function Header({ onOpenModal }) {
  return (
    <header className="site-header">
      <button className="new-obituary-button" onClick={onOpenModal}>
        + New Obituary
      </button>
      <h1>The Last Show</h1>
    </header>
  );
}

export default Header;
