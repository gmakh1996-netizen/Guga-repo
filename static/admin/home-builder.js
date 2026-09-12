/* მთავარი გვერდის კონსტრუქტორი: გადათრევა და ფილმების ძებნა.
   დამოკიდებულების გარეშე, ბრაუზერის საკუთარი drag-and-drop-ით. */
(function () {
  "use strict";

  function post(url, csrf, order) {
    var body = new FormData();
    body.append("_csrf", csrf);
    body.append("order", order.join(","));
    return fetch(url, { method: "POST", body: body, credentials: "same-origin" });
  }

  /* ერთი უნივერსალური გადათრევა: სახელურზე დაჭერით ელემენტი დროებით
     draggable ხდება, გაშვებისას კი ახალი თანმიმდევრობა სერვერს მიდის. */
  function sortable(container, itemSel, onDrop) {
    if (!container) return;
    var dragged = null;

    container.addEventListener("mousedown", function (e) {
      var handle = e.target.closest(".drag-handle");
      if (!handle || !container.contains(handle)) return;
      var item = handle.closest(itemSel);
      if (item) item.setAttribute("draggable", "true");
    });

    function clearDraggable() {
      container.querySelectorAll(itemSel + "[draggable]").forEach(function (i) {
        i.removeAttribute("draggable");
      });
    }
    container.addEventListener("mouseup", clearDraggable);

    container.addEventListener("dragstart", function (e) {
      var item = e.target.closest(itemSel);
      if (!item || !item.getAttribute("draggable")) return;
      dragged = item;
      item.classList.add("is-dragging");
      e.dataTransfer.effectAllowed = "move";
      try { e.dataTransfer.setData("text/plain", ""); } catch (err) {}
    });

    container.addEventListener("dragover", function (e) {
      if (!dragged) return;
      e.preventDefault();
      var over = e.target.closest(itemSel);
      if (!over || over === dragged || !container.contains(over)) return;
      var rect = over.getBoundingClientRect();
      var after = (e.clientY - rect.top) > rect.height / 2;
      container.insertBefore(dragged, after ? over.nextSibling : over);
    });

    container.addEventListener("drop", function (e) { e.preventDefault(); });

    container.addEventListener("dragend", function () {
      if (!dragged) return;
      dragged.classList.remove("is-dragging");
      dragged = null;
      clearDraggable();
      onDrop();
    });
  }

  function renumber(container, itemSel, numSel) {
    container.querySelectorAll(itemSel).forEach(function (item, i) {
      var n = item.querySelector(numSel);
      if (!n) return;
      // ფილმების ნომერი ახლა ველია (აკრეფადი), რიგების კი ჩვეულებრივი ტექსტი.
      // value-ს პროგრამულად დაყენება change-ს არ იწვევს, ანუ ფორმა არ გაიგზავნება.
      if (n.tagName === "INPUT") { n.value = i + 1; } else { n.textContent = i + 1; }
    });
  }

  // ---- რიგების თანმიმდევრობა ----
  var rowList = document.getElementById("rowList");
  if (rowList) {
    sortable(rowList, ".rowitem", function () {
      var ids = [].map.call(rowList.querySelectorAll(".rowitem"), function (el) {
        return el.dataset.rowId;
      });
      renumber(rowList, ".rowitem", ".rowitem__pos");
      post("/admin/home/reorder", rowList.dataset.csrf, ids);
    });
  }

  /* ძებნის ერთი დამხმარე: ველი + შედეგების კონტეინერი + რას ვაკეთებთ არჩევისას */
  function attachSearch(input, out, onPick) {
    var timer = null;
    input.addEventListener("input", function () {
      var q = input.value.trim();
      clearTimeout(timer);
      if (q.length < 2) { out.innerHTML = ""; return; }
      timer = setTimeout(function () {
        fetch("/admin/home/search?q=" + encodeURIComponent(q), { credentials: "same-origin" })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (!d.items || !d.items.length) {
              out.innerHTML = '<div class="pinsearch__none">ვერაფერი მოიძებნა</div>';
              return;
            }
            out.innerHTML = d.items.map(function (m) {
              return '<button type="button" class="pinsearch__item" data-type="' + m.media_type +
                '" data-id="' + m.id + '">' +
                (m.thumb ? '<img src="' + m.thumb + '" alt="">' : '<span class="pinlist__noimg">—</span>') +
                "<span>" + m.title + "</span>" +
                '<span class="muted">' + (m.year || "") + " · " + m.kind + "</span></button>";
            }).join("");
          });
      }, 250);
    });
    out.addEventListener("click", function (e) {
      var btn = e.target.closest(".pinsearch__item");
      if (btn) onPick(btn.dataset.type, btn.dataset.id);
    });
  }

  // ---- ნომრის პირდაპირ აკრეფა ----
  document.querySelectorAll(".pinlist__num input[type=number]").forEach(function (input) {
    input.addEventListener("change", function () { input.form.submit(); });
  });

  // ---- ჩანაცვლება ადგილზე ----
  document.querySelectorAll(".pinlist li").forEach(function (li) {
    var toggle = li.querySelector(".pinswap__toggle");
    var panel = li.querySelector(".pinswap");
    if (!toggle || !panel) return;
    var input = panel.querySelector(".pinswap__q");
    var out = panel.querySelector(".pinswap__out");
    var form = panel.querySelector(".pinswap__form");

    toggle.addEventListener("click", function () {
      panel.hidden = !panel.hidden;
      if (!panel.hidden) input.focus();
    });
    attachSearch(input, out, function (type, id) {
      form.querySelector('input[name="media_type"]').value = type;
      form.querySelector('input[name="item_id"]').value = id;
      form.submit();
    });
  });

  // ---- ფილმების თანმიმდევრობა თითო რიგში ----
  document.querySelectorAll(".pinbox").forEach(function (box) {
    var list = box.querySelector(".pinlist");
    if (list) {
      sortable(list, "li", function () {
        var ids = [].map.call(list.querySelectorAll("li"), function (li) {
          return li.dataset.pk;
        });
        renumber(list, "li", ".pinlist__n");
        post("/admin/home/" + box.dataset.row + "/items/reorder", box.dataset.csrf, ids);
      });
    }

    // ---- ძებნა და დამატება ----
    var input = box.querySelector(".pinsearch__q");
    var out = box.querySelector(".pinsearch__out");
    var form = box.querySelector(".pinsearch__add");
    if (!input || !out || !form) return;

    attachSearch(input, out, function (type, id) {
      form.querySelector('input[name="media_type"]').value = type;
      form.querySelector('input[name="item_id"]').value = id;
      form.submit();
    });
  });
})();
