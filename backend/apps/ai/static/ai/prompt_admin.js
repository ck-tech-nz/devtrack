// Prompt 管理:让"模型"输入框的 <datalist> 跟随"LLM 配置"过滤。
// 后端在 #id_llm_model 上放了 data-models-map='{"<cfg_id>": [models...]}'
// 改 #id_llm_config 时按映射重建 <datalist> 内的 <option>。
(function () {
  function init() {
    var modelInput = document.getElementById("id_llm_model");
    var cfgSel = document.getElementById("id_llm_config");
    if (!modelInput || !cfgSel) return;

    var datalistId = modelInput.getAttribute("list");
    var datalist = datalistId && document.getElementById(datalistId);
    if (!datalist) return;

    var raw = modelInput.getAttribute("data-models-map");
    if (!raw) return;
    var map;
    try { map = JSON.parse(raw); } catch (_e) { return; }

    function refresh() {
      var key = cfgSel.value || "";
      var models = map[key] || [];
      datalist.innerHTML = "";
      models.forEach(function (m) {
        var o = document.createElement("option");
        o.value = m;
        datalist.appendChild(o);
      });
    }

    cfgSel.addEventListener("change", refresh);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
