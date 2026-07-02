(function(PFNConfig){
    var root = '/infrapredial-pfnweb',
        ts = +Date.now();
    PFNConfig.config({
        appName: 'OrdemServicoModule',
        jsFiles: [
            root + '/v2/spas/manutencao/ordem-servico/ordem-servico-module-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/validar-form.directive-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/valor-monetario.directive-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/valor-decimal-mask.directive-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/ordem-servico-services-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/listar/ordem-servico-contrato-listar-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/listar/ordem-servico-listar-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/ordem-servico-detalhar-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/ordem-servico-detalhar-laudo-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/ordem-servico-orcamento-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/ordem-servico-rat-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/laudo-utils-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/laudo-relatorio-casa-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/steps-components/step-avaliacao-component-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/steps-components/step-vaga-garagem-component-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/steps-components/step-manifestacao-garantia-component-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/laudo-relatorio-apartamento-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/laudo-relatorio-terreno-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/laudo-relatorio-comercial-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/laudo/laudo-relatorio-equipamento-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/ordem-servico-documento-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/detalhar/ordem-servico-fiscalizacao-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/controle-material/cadastrar/cadastrar-material-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/contrato/home-contrato-controller-min.js?_t=' + ts,
            root + '/v2/spas/manutencao/ordem-servico/contrato/contrato-documento-controller.js?_t=' + ts
        ]
    });
    PFNConfig.config({
        appName: 'InfrapredialAPP',
        jsFiles: [
            root + '/v2/spas/infrapredial-api-config-v2-min.js?_t=' + ts
        ]
    });
})(PFNConfig);
