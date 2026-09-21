function PagePlaceholder({ eyebrow, title, description, children }) {

  return (
    <section className="page-section">
      <div className="page-heading">
        <div>
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        {children}
      </div>
    </section>
  )
}

export default PagePlaceholder