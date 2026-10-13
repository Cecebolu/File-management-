// Mobile sidebar toggle
document.querySelectorAll("[data-sidebar-toggle]").forEach(function (el) {
    el.addEventListener("click", function () {
        document.body.classList.toggle("sidebar-open");
    });
});

// Show / hide password
document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
        var input = document.getElementById(button.dataset.togglePassword);
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        button.querySelector("i").className = show ? "bi bi-eye-slash" : "bi bi-eye";
    });
});

// Fade out success / info messages after a few seconds
document.querySelectorAll(".flash-stack .alert-success, .flash-stack .alert-info").forEach(function (alert) {
    setTimeout(function () {
        bootstrap.Alert.getOrCreateInstance(alert).close();
    }, 5000);
});

// Ask before submitting destructive forms (message kept out of inline JS so quotes in names are safe)
document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
        if (!confirm(form.dataset.confirm)) {
            event.preventDefault();
        }
    });
});

// Filter a list by typing (e.g. people on the folder share page)
document.querySelectorAll("[data-filter-list]").forEach(function (input) {
    var list = document.getElementById(input.dataset.filterList);
    input.addEventListener("input", function () {
        var term = input.value.trim().toLowerCase();
        list.querySelectorAll("[data-filter-text]").forEach(function (item) {
            item.style.display = item.dataset.filterText.toLowerCase().includes(term) ? "" : "none";
        });
    });
});

// Filter table rows by typing
document.querySelectorAll("[data-filter-table]").forEach(function (input) {
    var table = document.getElementById(input.dataset.filterTable);
    if (!table) return;
    var empty = table.querySelector(".no-results");
    input.addEventListener("input", function () {
        var term = input.value.trim().toLowerCase();
        var shown = 0;
        table.querySelectorAll("tbody tr:not(.no-results)").forEach(function (row) {
            var match = row.textContent.toLowerCase().includes(term);
            row.style.display = match ? "" : "none";
            if (match) shown++;
        });
        if (empty) empty.style.display = shown ? "none" : "table-row";
    });
});

// Drop zones: highlight while dragging and show what was picked
document.querySelectorAll(".dropzone").forEach(function (zone) {
    var input = zone.querySelector("input[type=file]");
    var summary = document.getElementById(zone.dataset.summary);
    ["dragenter", "dragover"].forEach(function (name) {
        zone.addEventListener(name, function () { zone.classList.add("is-dragover"); });
    });
    ["dragleave", "drop"].forEach(function (name) {
        zone.addEventListener(name, function () { zone.classList.remove("is-dragover"); });
    });
    input.addEventListener("change", function () {
        if (!summary) return;
        var files = input.files;
        if (!files.length) {
            summary.textContent = "";
            return;
        }
        if (input.hasAttribute("webkitdirectory")) {
            var folder = files[0].webkitRelativePath.split("/")[0];
            summary.innerHTML = "";
            summary.append("Folder “" + folder + "” · " + files.length + " file" + (files.length === 1 ? "" : "s"));
        } else if (files.length === 1) {
            summary.textContent = files[0].name;
        } else {
            summary.textContent = files.length + " files selected";
        }
    });
});
