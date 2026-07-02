(function(PFNConfig) {
    var root = '/aceite-pfnweb',
        ts = +Date.now();
    PFNConfig.config({
        appName: 'AceiteModule',
        jsFiles: [
            root + '/v2/spas/aceite-module-min.js?_t=' + ts,
            root + '/v2/spas/aceite.service-min.js?_t=' + ts,
            root + '/v2/spas/documento-service-min.js?_t=' + ts,
            root + '/v2/spas/aceite-filtros.filter-min.js?_t=' + ts,
            root + '/v2/scripts/diretivas-angular/pdf-viewer/angular-sanitize-min.js?_t=' + ts,
            root + '/v2/scripts/diretivas-angular/pdf-viewer/diretiva-pdf-viewer-min.js?_t=' + ts,
            root + '/v2/spas/listarPedidosCompra/listar-pedidos-fornecedor.controller-min.js?_t=' + ts,
            root + '/v2/spas/detalhar/detalhar-pedido.controller-min.js?_t=' + ts,
            root + '/v2/spas/manterObjetoCompra/listaBensAtaRegistroPreco/listar-bens-cadastrados-controller-min.js?_t=' + ts,
            root + '/v2/spas/manterObjetoCompra/manterBens/manter-bens-controller-min.js?_t=' + ts,
            root + '/v2/spas/manterObjetoCompra/manterBensContrato/manter-bens-contrato-controller-min.js?_t=' + ts,
            root + '/v2/spas/documentoFiscal/listarDocumentoFiscal/listar-documento-fiscal-controller-min.js?_t=' + ts,
            root + '/v2/spas/documentoFiscal/manterDocumentoFiscal/manter-documento-fiscal-controller-min.js?_t=' + ts,
            root + '/v2/spas/documentoFiscal/detalharDocumentoFiscal/detalhar-documento-fiscal-controller-min.js?_t=' + ts,
            root + '/v2/spas/notificacoes/listarNotificacoes/listar-notificacoes-controller-min.js?_t=' + ts,
            root + '/v2/spas/manterObjetoCompra/inclusaoMassificadaBens/visualizacao-inclusao-massificada-bens-controller-min.js?_t=' + ts,
            root + '/v2/spas/documentoFiscal/inclusaoMassificadaDocumentosFiscais/visualizacao-inclusao-massificada-documentos-controller-min.js?_t=' + ts,
            root + '/v2/spas/manterObjetoCompra/cabecalhoListarBens/cabecalho-lista-bens-controller-min.js?_t=' + ts,
            root + '/v2/spas/manterObjetoCompra/listaBensContrato/lista-bens-contrato-controller-min.js?_t=' + ts,
            root + '/v2/utils/aceite-utils-min.js?_t=' + ts
        ]
    });
    PFNConfig.config({
        appName: 'AceiteAPP',
        jsFiles: [
            root + '/v2/spas/aceite-web-config-min.js?_t=' + ts
        ]
    });
})(PFNConfig);