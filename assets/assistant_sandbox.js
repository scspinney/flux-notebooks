document.addEventListener("click", function (e) {
    if (e.target.classList.contains("flux-plot-thumb")) {
        const full = e.target.dataset.fullres;   // ✅ must be data-fullres in HTML

        const modal = document.getElementById("flux-image-modal");
        const modalImg = document.getElementById("flux-modal-image");

        if (!modal || !modalImg) return;  // ✅ safety

        modalImg.src = "data:image/png;base64," + full;
        modal.style.display = "flex";
    }
});

// ✅ close modal on click
document.addEventListener("click", function (e) {
    const modal = document.getElementById("flux-image-modal");
    if (!modal) return;

    if (e.target.id === "flux-image-modal" || e.target.id === "flux-modal-image") {
        modal.style.display = "none";
    }
});
