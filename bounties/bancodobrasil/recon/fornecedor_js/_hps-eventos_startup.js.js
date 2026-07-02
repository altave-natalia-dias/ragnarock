(function(PFNConfig){
	
	var	root = '/hps-eventos',
		ts = +Date.now();

	PFNConfig.config({
		appName: 'HPS_Eventos_Module',
		jsFiles: [
			root+'/components/angular_animate/1.7.9/angular-animate.min.js?_t='+ts,
			root+'/components/angular_aria/1.7.9/angular-aria.min.js?_t='+ts,
			root+'/components/angular_messages/1.7.9/angular-messages.min.js?_t='+ts,
			root+'/components/angular_material/1.1.21/angular-material.min.js?_t='+ts,
			root+'/components/pagination/directive-pagination-min.js?_t='+ts,
			root+'/components/validation/directive-diff-days-min.js?_t='+ts,
			root+'/components/loading/directive-loading-min.js?_t='+ts,
			root+'/components/filters/hps-filters-min.js?_t='+ts,
			root+'/components/filters/cut-filter-min.js?_t='+ts,
			root+'/v1/spas/main-module-min.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/eventoDeVulto/vulto-evento-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/eventoDeVulto/directive-vulto-evento.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/historico/historico-evento-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/historico/directive-historico-evento.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/contatos/contatos-evento-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/contatos/directive-contatos-evento.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/eventoVulto/evento-vulto-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/eventoVulto/directive-evento-vulto.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/eventosRelacionados/eventos-relacionados-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/eventosRelacionados/directive-eventos-relacionados.js?_t='+ts,
			root+'/v1/spas/evento/listar/lista-eventos-controller.js?_t='+ts,
			root+'/v1/spas/evento/eventos-services.js?_t='+ts,
			root+'/v1/spas/evento/detalhar/detalhes-evento-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/detalhes-evento-completo-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalharFechado/detalhes-evento-fechado-controller.js?_t='+ts,
			root+'/v1/spas/evento/fechadoListagem/fechado-listagem-controller.js?_t='+ts,
			root+'/v1/spas/evento/fechadoListagem/fechado-listagem-services.js?_t='+ts,
			root+'/v1/spas/evento/detalharFechado/historico/historico-evento-fechado-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalharFechado/historico/directive-historico-evento-fechado.js?_t='+ts,
			root+'/v1/spas/evento/inclusao/inclusao-evento-controller.js?_t='+ts,
            root+'/v1/spas/evento/conciliacao/conciliacao-evento-controller.js?_t='+ts,
            root+'/v1/spas/evento/relatorios/relatorio-evento-controller.js?_t='+ts,
			root+'/v1/spas/evento/solicitacaoRelatorio/solicitacao-relatorio-controller.js?_t='+ts,
			root+'/v1/spas/evento/util/UtilListaEventos.js?_t='+ts,
			root+'/v1/spas/evento/cripto/hpscripto-min.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/anexos/anexos-evento-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/anexos/directive-anexos-evento.js?_t='+ts,
			root+'/v1/spas/evento/detalhamentoCompleto/anexos/anexos-evento-services.js?_t='+ts,
			root+'/v1/spas/evento/detalharFechado/anexos/anexos-evento-fechado-controller.js?_t='+ts,
			root+'/v1/spas/evento/detalharFechado/anexos/directive-anexos-fechado-evento.js?_t='+ts,
			root+'/v1/spas/evento/detalharFechado/anexos/anexos-evento-fechado-services.js?_t='+ts,
 		]
	});

	PFNConfig.config({
		appName: 'HPS_Eventos_APP',
		jsFiles: [
			root+'/v1/spas/main-app-min.js?_t='+ts
		]
	});

})(PFNConfig);
