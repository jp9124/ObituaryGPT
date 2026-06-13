function Header({ onOpenModal }) {
  return (
    <header className="site-header">
      <button className="new-obituary-button" onClick={onOpenModal}>
        + New Obituary
      </button>
      <h1>ObituaryGPT</h1>
    </header>
  );
}

export default Header;
