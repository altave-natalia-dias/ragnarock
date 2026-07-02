(function (PFNConfig) {
  var root = "/gestaousuario";
  var ts = +Date.now();
  PFNConfig.config({
    appName: "GestaoUsuarioModule",
    jsFiles: [
      root + "/v1/spas/gestaousuario-module-min.js?_t=" + ts,
      root + "/v1/spas/gestaousuario-constants-min.js?_t=" + ts,
      root + "/v1/spas/gestaousuario/gestaousuario-service-min.js?_t=" + ts,
      root +
        "/v1/spas/gestaousuario/listar/usuarios-listar-controller-min.js?_t=" +
        ts,
      root +
        "/v1/spas/gestaousuario/cadastrar/usuarios-cadastrar-controller-min.js?_t=" +
        ts,
      root +
        "/v1/spas/gestaousuario/cadastrar/usuarios-confirmar-controller-min.js?_t=" +
        ts,
      root +
        "/v1/spas/gestaousuario/detalhar/usuarios-detalhar-controller-min.js?_t=" +
        ts,
      root +
        "/v1/spas/gestaousuario/perfil/usuario-perfil-controller-min.js?_t=" +
        ts,
      root +
        "/v1/spas/gestaousuario/transacoes/usuarios-transacoes-controller-min.js?_t=" +
        ts,
    ],
  });
  PFNConfig.config({
    appName: "GestaoUsuarioAPP",
    jsFiles: [root + "/v1/spas/gestaousuario-app-min.js?_t=" + ts],
  });
})(PFNConfig);
