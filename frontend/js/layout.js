async function initLayout() {
  const sidebarContainer = document.getElementById("sidebar");
  if (!sidebarContainer) return;

  try {
    const response = await fetch("/components/sidebar.html");
    sidebarContainer.innerHTML = await response.text();

    const currentPage = document.body.dataset.page;
    sidebarContainer.querySelectorAll("a[data-page]").forEach((link) => {
      if (link.dataset.page === currentPage) {
        link.classList.add("active");
      }
    });
  } catch (err) {
    sidebarContainer.innerHTML = `<p class="error">Error al cargar el menú</p>`;
  }
}

initLayout();
