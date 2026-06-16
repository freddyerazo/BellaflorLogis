import { apiGet, apiPost, apiPut, apiDelete } from "./api.js";

export async function initCrudPage(config) {
  const {
    endpoint,
    title,
    mountSelector = "#content",
    idField = "id",
    columns,
    fields,
    allowCreate = true,
    allowDelete = true,
  } = config;

  const mount = document.querySelector(mountSelector);
  if (!mount) return;

  const colCount = columns.length + 1;

  mount.innerHTML = `
    <div class="page-header">
      <h1>${title}</h1>
      ${allowCreate ? '<button type="button" class="btn btn-primary" data-role="new">+ Nuevo</button>' : ""}
    </div>
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            ${columns.map((c) => `<th>${c.label}</th>`).join("")}
            <th class="actions-col">Acciones</th>
          </tr>
        </thead>
        <tbody data-role="table-body">
          <tr><td colspan="${colCount}" class="loading">Cargando...</td></tr>
        </tbody>
      </table>
    </div>
    <dialog data-role="dialog">
      <form data-role="form">
        <h2 data-role="dialog-title">Nuevo</h2>
        <div data-role="form-fields"></div>
        <p class="form-error" data-role="form-error"></p>
        <div class="dialog-actions">
          <button type="button" class="btn btn-secondary" data-role="cancel">Cancelar</button>
          <button type="submit" class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </dialog>
  `;

  const tableBody = mount.querySelector('[data-role="table-body"]');
  const dialog = mount.querySelector('[data-role="dialog"]');
  const form = mount.querySelector('[data-role="form"]');
  const formFields = mount.querySelector('[data-role="form-fields"]');
  const formError = mount.querySelector('[data-role="form-error"]');
  const dialogTitle = mount.querySelector('[data-role="dialog-title"]');

  let editingId = null;
  let currentRows = [];
  const optionsCache = {};

  async function loadOptions() {
    for (const field of fields) {
      if (field.optionsEndpoint) {
        optionsCache[field.name] = await apiGet(field.optionsEndpoint);
      }
    }
  }

  function formatCell(row, column) {
    const value = row[column.key];
    if (column.format === "active-badge") {
      return value
        ? '<span class="badge badge-active">Activo</span>'
        : '<span class="badge badge-inactive">Inactivo</span>';
    }
    if (value === null || value === undefined || value === "") return "-";
    return String(value);
  }

  async function loadTable() {
    tableBody.innerHTML = `<tr><td colspan="${colCount}" class="loading">Cargando...</td></tr>`;
    try {
      currentRows = await apiGet(endpoint);
      if (!currentRows.length) {
        tableBody.innerHTML = `<tr><td colspan="${colCount}" class="empty">Sin registros</td></tr>`;
        return;
      }

      tableBody.innerHTML = currentRows
        .map((row) => {
          const cells = columns.map((c) => `<td>${formatCell(row, c)}</td>`).join("");
          const deleteBtn = allowDelete
            ? `<button type="button" class="btn-link btn-danger" data-action="delete" data-id="${row[idField]}">Eliminar</button>`
            : "";
          return `<tr>
            ${cells}
            <td class="actions-col">
              <button type="button" class="btn-link" data-action="edit" data-id="${row[idField]}">Editar</button>
              ${deleteBtn}
            </td>
          </tr>`;
        })
        .join("");

      tableBody.querySelectorAll('[data-action="edit"]').forEach((btn) => {
        btn.addEventListener("click", () => openEdit(btn.dataset.id));
      });
      tableBody.querySelectorAll('[data-action="delete"]').forEach((btn) => {
        btn.addEventListener("click", () => handleDelete(btn.dataset.id));
      });
    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="${colCount}" class="error">Error: ${err.message}</td></tr>`;
    }
  }

  function fieldInputHtml(field, value) {
    const id = `field-${field.name}`;
    const required = field.required ? "required" : "";

    switch (field.type) {
      case "checkbox":
        return `<input type="checkbox" id="${id}" name="${field.name}" ${value ? "checked" : ""} />`;

      case "select": {
        const opts = optionsCache[field.name] || [];
        const optionsHtml = opts
          .map((opt) => {
            const optValue = field.optionValue ? field.optionValue(opt) : opt.id;
            const optLabel = field.optionLabel ? field.optionLabel(opt) : opt.name;
            const isSelected = value !== undefined && value !== null && String(value) === String(optValue);
            return `<option value="${optValue}" ${isSelected ? "selected" : ""}>${optLabel}</option>`;
          })
          .join("");

        let placeholder = "";
        const hasValue = value !== undefined && value !== null && value !== "";
        if (!field.required) {
          placeholder = `<option value="">-- Ninguno --</option>`;
        } else if (!hasValue) {
          placeholder = `<option value="" disabled selected>-- Seleccione --</option>`;
        }

        return `<select id="${id}" name="${field.name}" ${required}>${placeholder}${optionsHtml}</select>`;
      }

      case "textarea":
        return `<textarea id="${id}" name="${field.name}" ${required}>${value ?? ""}</textarea>`;

      case "number": {
        const step = field.step || "any";
        return `<input type="number" step="${step}" id="${id}" name="${field.name}" value="${value ?? ""}" ${required} />`;
      }

      case "date":
        return `<input type="date" id="${id}" name="${field.name}" value="${value ?? ""}" ${required} />`;

      default:
        return `<input type="text" id="${id}" name="${field.name}" value="${value ?? ""}" ${required} />`;
    }
  }

  function renderForm(row) {
    const isCreate = row === null;
    const visibleFields = fields.filter((f) => !(isCreate && f.editOnly));

    formFields.innerHTML = visibleFields
      .map((field) => {
        const value = isCreate ? field.default : row[field.name];
        const input = fieldInputHtml(field, value);

        if (field.type === "checkbox") {
          return `
            <div class="form-group form-group-checkbox">
              <label for="field-${field.name}">${input} ${field.label}</label>
            </div>`;
        }

        return `
          <div class="form-group">
            <label for="field-${field.name}">${field.label}</label>
            ${input}
          </div>`;
      })
      .join("");
  }

  function openCreate() {
    editingId = null;
    dialogTitle.textContent = `Nuevo`;
    formError.textContent = "";
    renderForm(null);
    dialog.showModal();
  }

  function openEdit(id) {
    const row = currentRows.find((r) => String(r[idField]) === String(id));
    if (!row) return;
    editingId = id;
    dialogTitle.textContent = `Editar`;
    formError.textContent = "";
    renderForm(row);
    dialog.showModal();
  }

  async function handleDelete(id) {
    if (!confirm("¿Está seguro de eliminar este registro?")) return;
    try {
      await apiDelete(`${endpoint}/${id}`);
      await loadTable();
    } catch (err) {
      alert(`Error al eliminar: ${err.message}`);
    }
  }

  function collectFormData() {
    const isCreate = editingId === null;
    const visibleFields = fields.filter((f) => !(isCreate && f.editOnly));
    const data = {};

    for (const field of visibleFields) {
      const input = formFields.querySelector(`[name="${field.name}"]`);
      if (field.type === "checkbox") {
        data[field.name] = input.checked;
      } else if (field.type === "number") {
        data[field.name] = input.value === "" ? null : Number(input.value);
      } else {
        data[field.name] = input.value === "" ? null : input.value;
      }
    }

    return data;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.textContent = "";
    const data = collectFormData();

    try {
      if (editingId !== null) {
        await apiPut(`${endpoint}/${editingId}`, data);
      } else {
        await apiPost(endpoint, data);
      }
      dialog.close();
      await loadTable();
    } catch (err) {
      formError.textContent = err.message;
    }
  });

  mount.querySelector('[data-role="cancel"]')?.addEventListener("click", () => dialog.close());
  mount.querySelector('[data-role="new"]')?.addEventListener("click", openCreate);

  await loadOptions();
  await loadTable();
}
