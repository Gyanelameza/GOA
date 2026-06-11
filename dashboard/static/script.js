document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const tableList = document.getElementById('table-list');
    const tableHeaders = document.getElementById('table-headers');
    const tableRows = document.getElementById('table-rows');
    const rowCountBadge = document.getElementById('row-count-badge');
    const currentViewTitle = document.getElementById('current-view-title');
    const currentViewDesc = document.getElementById('current-view-desc');
    const dashboardSummary = document.getElementById('dashboard-summary');
    
    const consolePanel = document.getElementById('console-panel');
    const btnShowConsole = document.getElementById('btn-show-console');
    const btnCloseConsole = document.getElementById('btn-close-console');
    const sqlEditor = document.getElementById('sql-editor');
    const btnExecuteQuery = document.getElementById('btn-execute-query');
    const consoleOutput = document.getElementById('console-output');
    const btnRefresh = document.getElementById('btn-refresh');

    let activeTable = null;

    // Load table list
    async function loadTables() {
        tableList.innerHTML = '<li class="loading-tables"><i class="fa-solid fa-circle-notch fa-spin"></i> Cargando tablas...</li>';
        try {
            const response = await fetch('/api/tables');
            const data = await response.json();
            
            if (data.error) {
                tableList.innerHTML = `<li class="loading-tables text-error"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${data.error}</li>`;
                return;
            }

            tableList.innerHTML = '';
            
            let totalRows = 0;
            data.tables.forEach(table => {
                totalRows += table.rows;
                
                const li = document.createElement('li');
                li.setAttribute('data-name', table.name);
                if (activeTable === table.name) {
                    li.className = 'active';
                }
                
                li.innerHTML = `
                    <div class="table-info">
                        <span class="table-name">${table.name}</span>
                        <span class="table-rows">${table.rows} filas</span>
                    </div>
                    <i class="fa-solid fa-chevron-right chevron"></i>
                `;
                
                li.addEventListener('click', () => {
                    document.querySelectorAll('#table-list li').forEach(item => item.classList.remove('active'));
                    li.classList.add('active');
                    viewTable(table.name);
                    
                    // Collapse sidebar on mobile after selecting a table
                    if (window.innerWidth <= 768 && sidebar && !sidebar.classList.contains('collapsed')) {
                        toggleSidebar();
                    }
                });
                
                tableList.appendChild(li);
            });

            // Update Summary Dashboard
            updateSummaryCards(data.tables.length, totalRows);

        } catch (error) {
            tableList.innerHTML = `<li class="loading-tables text-error"><i class="fa-solid fa-triangle-exclamation"></i> Error de conexión</li>`;
            console.error('Error loading tables:', error);
        }
    }

    // Update Summary Dashboard Cards
    function updateSummaryCards(tableCount, rowCount) {
        dashboardSummary.innerHTML = `
            <div class="stat-card glass">
                <div class="stat-icon"><i class="fa-solid fa-table-list"></i></div>
                <div class="stat-info">
                    <h4>Tablas Totales</h4>
                    <p>${tableCount}</p>
                </div>
            </div>
            <div class="stat-card glass">
                <div class="stat-icon"><i class="fa-solid fa-database"></i></div>
                <div class="stat-info">
                    <h4>Filas Totales</h4>
                    <p>${rowCount}</p>
                </div>
            </div>
            <div class="stat-card glass">
                <div class="stat-icon" style="color: var(--accent-emerald); background-color: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.2);"><i class="fa-solid fa-plug"></i></div>
                <div class="stat-info">
                    <h4>Base de Datos</h4>
                    <p style="color: var(--accent-emerald); font-size: 16px; margin-top: 4px; font-weight: 600;">PostgreSQL (Online)</p>
                </div>
            </div>
        `;
    }

    // View specific table data
    async function viewTable(tableName) {
        activeTable = tableName;
        currentViewTitle.textContent = `Tabla: ${tableName}`;
        currentViewDesc.textContent = `Visualizando estructura y primeros 100 registros.`;
        
        tableHeaders.innerHTML = '<tr><th>Cargando columnas...</th></tr>';
        tableRows.innerHTML = '<tr><td class="empty-state"><i class="fa-solid fa-circle-notch fa-spin"></i> Cargando datos...</td></tr>';
        rowCountBadge.textContent = 'Cargando...';

        try {
            const response = await fetch(`/api/table/${tableName}`);
            const data = await response.json();
            
            if (data.error) {
                tableRows.innerHTML = `<tr><td class="empty-state text-error"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${data.error}</td></tr>`;
                return;
            }

            // Headers
            tableHeaders.innerHTML = '';
            data.columns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col;
                tableHeaders.appendChild(th);
            });

            // Rows
            tableRows.innerHTML = '';
            rowCountBadge.textContent = `${data.rows.length} filas`;
            
            if (data.rows.length === 0) {
                tableRows.innerHTML = `
                    <tr>
                        <td colspan="${data.columns.length}" class="empty-state">
                            <i class="fa-solid fa-folder-open"></i>
                            <p>Esta tabla está vacía</p>
                        </td>
                    </tr>
                `;
                return;
            }

            data.rows.forEach(row => {
                const tr = document.createElement('tr');
                row.forEach(val => {
                    const td = document.createElement('td');
                    td.textContent = val !== null ? val : 'NULL';
                    if (val === 'NULL' || val === null) {
                        td.style.color = 'var(--text-muted)';
                        td.style.fontStyle = 'italic';
                    }
                    tr.appendChild(td);
                });
                tableRows.appendChild(tr);
            });

        } catch (error) {
            tableRows.innerHTML = `<tr><td class="empty-state text-error"><i class="fa-solid fa-triangle-exclamation"></i> Error de conexión</td></tr>`;
            console.error('Error viewing table:', error);
        }
    }

    // Toggle Console Panel
    btnShowConsole.addEventListener('click', () => {
        if (consolePanel.style.display === 'none') {
            consolePanel.style.display = 'flex';
            sqlEditor.focus();
        } else {
            consolePanel.style.display = 'none';
        }
    });

    btnCloseConsole.addEventListener('click', () => {
        consolePanel.style.display = 'none';
    });

    // Run custom SQL query
    btnExecuteQuery.addEventListener('click', async () => {
        const query = sqlEditor.value.trim();
        if (!query) {
            consoleOutput.innerHTML = '<div class="output-error">La consulta está vacía.</div>';
            return;
        }

        consoleOutput.innerHTML = '<div><i class="fa-solid fa-circle-notch fa-spin"></i> Ejecutando consulta SQL...</div>';
        
        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: query })
            });
            const data = await response.json();

            if (data.error) {
                consoleOutput.innerHTML = `<div class="output-error"><i class="fa-solid fa-circle-xmark"></i> ERROR:<br>${data.error}</div>`;
                return;
            }

            if (data.type === 'select') {
                if (data.rows.length === 0) {
                    consoleOutput.innerHTML = '<div class="output-success"><i class="fa-solid fa-circle-check"></i> Consulta ejecutada con éxito (0 filas devueltas).</div>';
                    return;
                }

                // Render result table in console
                let headersHtml = data.columns.map(col => `<th>${col}</th>`).join('');
                let rowsHtml = data.rows.map(row => {
                    let cells = row.map(val => `<td>${val !== null ? val : 'NULL'}</td>`).join('');
                    return `<tr>${cells}</tr>`;
                }).join('');

                consoleOutput.innerHTML = `
                    <div class="output-success">
                        <i class="fa-solid fa-circle-check"></i> Consulta SELECT completada con éxito. Registros devueltos: ${data.rows.length}
                    </div>
                    <div class="console-table-wrapper">
                        <table class="console-table">
                            <thead>
                                <tr>${headersHtml}</tr>
                            </thead>
                            <tbody>
                                ${rowsHtml}
                            </tbody>
                        </table>
                    </div>
                `;
            } else {
                consoleOutput.innerHTML = `
                    <div class="output-success">
                        <i class="fa-solid fa-circle-check"></i> ${data.message}
                    </div>
                `;
            }

            // Refresh table list and active view to reflect updates
            loadTables();
            if (activeTable) {
                viewTable(activeTable);
            }

        } catch (error) {
            consoleOutput.innerHTML = `<div class="output-error"><i class="fa-solid fa-circle-xmark"></i> Error de conexión</div>`;
            console.error('Error running query:', error);
        }
    });

    // Refresh button
    btnRefresh.addEventListener('click', () => {
        loadTables();
        if (activeTable) {
            viewTable(activeTable);
        }
    });

    // Collapsible Sidebar logic for mobile/tablet viewports
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (sidebar && window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
    }

    function toggleSidebar() {
        if (sidebar) {
            sidebar.classList.toggle('collapsed');
            if (window.innerWidth <= 768) {
                if (!sidebar.classList.contains('collapsed')) {
                    if (sidebarOverlay) sidebarOverlay.classList.add('active');
                } else {
                    if (sidebarOverlay) sidebarOverlay.classList.remove('active');
                }
            }
        }
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', toggleSidebar);
    }
 
    // Initial load
    loadTables();
});
