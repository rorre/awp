// ==UserScript==
// @name         IRS Autofill
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  try to take over the world!
// @author       You
// @match        https://*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=academic.ui.ac.id
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  // Your code here...
  window.irsfill = (matkuls) => {
    let matkulCollection = [];
    function findRows(selectedSubjects) {
      for (let elem of selectedSubjects) {
        let matkulElems = [];
        let [matkul, priorities] = elem;
        for (let idx of priorities) {
          matkulElems.push(document.getElementsByName(matkul)[idx]);
        }
        matkulCollection.push(matkulElems);
      }
      return matkulCollection;
    }

    function isCapable(elem) {
      const baseElem = elem.parentElement.parentElement;
      const stuffs = baseElem.querySelectorAll(".ri");
      return parseInt(stuffs[0].textContent) > parseInt(stuffs[1].textContent);
    }

    // let matkuls = [
    //   ["c[CSGE602012_01.00.12.01-2020]", [0]], // Aljabar Linier A
    //   ["c[CSGE601021_01.00.12.01-2020]", [3]], // DDP 2-D
    //   ["c[CSCM601213_01.00.12.01-2020]", [1]], // Kalkulus 2 C
    //   ["c[CSCM601252_01.00.12.01-2020]", [1]], // POK B
    //   ["c[CSGE601011_06.00.12.01-2020]", [2]], // MatDis 2-F
    //   ["c[UIGE600006_01.00.12.01-2020]", [5]], // MPK Terintegrasi-F
    // ];

    // let matkuls: MatkulSelection[] = [
    //     ['c[LWIA600007_06.00.05.01-2020]', [0, 2, 1]],
    //     ['c[LWPE600103_06.00.05.01-2013]', [0]],
    // ]

    for (let row of findRows(matkuls)) {
      let isSelected = false;
      let isBackup = false;
      for (let elem of row) {
        if (isCapable(elem)) {
          elem.click();
          let className =
            elem.parentElement.nextElementSibling.textContent.trim();
          let msgStart = isBackup ? "%cSelected BACKUP:" : "%cSelected:";
          console.log(msgStart, "background: aqua; color: black;", className);
          isSelected = true;
          break;
        } else {
          isBackup = true;
        }
      }
      if (!isSelected) {
        let matkulName = row[0].getAttribute("name");
        console.log(
          `%cWARN:`,
          "background: yellow; color: black;",
          `Matkul ${matkulName} is fully taken.`
        );
      }
    }
    window.scrollTo(0, document.body.scrollHeight);
  };
})();
