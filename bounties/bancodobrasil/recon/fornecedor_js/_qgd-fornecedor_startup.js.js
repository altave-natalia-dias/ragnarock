(function (PFNConfig) {

	let root = '/qgd-fornecedor',
		ts = +Date.now();

	PFNConfig.config({
		appName: 'QGD_Fornecedor_Module',
		jsFiles: [
			
			root + '/v1/spas/main-module-min.js?_t=' + ts,
			root + '/v1/spas/menu/menu.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/consultar/consultar-agendamento-services.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/consultar/consultar-agendamento-controller.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/consultar-realizados/consultar-agendamentos-realizados-services.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/consultar-realizados/consultar-agendamentos-realizados-controller.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/detalhar-realizados/detalhar-agendamentos-realizados-services.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/detalhar-realizados/detalhar-agendamentos-realizados-controller.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/solicitar/solicitar-agendamento-services.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/solicitar/solicitar-agendamento-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/consultar/consultar-pendencias-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/consultar/consultar-pendencias-services.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/consultas-realizadas/consultar-pendencias-realizadas-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/consultas-realizadas/consultar-pendencias-realizadas-services.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/detalhar-realizados/detalhar-pendencias-realizadas-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/detalhar-realizados/detalhar-pendencias-realizadas-services.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/registrar/registrar-pendencias-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/registrar/registrar-pendencias-services.js?_t=' + ts,
			
			root + '/v1/spas/NCD/inviabilidade/consultar/consultar-inviabilidade-services.js?_t=' + ts,
			root + '/v1/spas/NCD/inviabilidade/consultar/consultar-inviabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/inviabilidade/registrar/registrar-inviabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/inviabilidade/registrar/registrar-inviabilidade-services.js?_t=' + ts,

			root + '/v1/spas/relatorios/agendamento/relatorios-agendamento-controller.js?_t=' + ts,
			root + '/v1/spas/relatorios/agendamento/relatorios-agendamento-service.js?_t=' + ts,
			root + '/v1/spas/relatorios/pendencia/escolha-relatorios-pendencia-controller.js?_t=' + ts,
			root + '/v1/spas/relatorios/pendencia/relatorios-pendencia-controller.js?_t=' + ts,
			root + '/v1/spas/relatorios/pendencia/relatorios-pendencia-service.js?_t=' + ts,
			root + '/v1/spas/relatorios/inviabilidade/relatorios-inviabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/relatorios/inviabilidade/relatorios-inviabilidade-service.js?_t=' + ts,
			root + '/v1/spas/relatorios/planta-circuito/relatorios-planta-circuito-controller.js?_t=' + ts,
			root + '/v1/spas/relatorios/planta-circuito/relatorios-planta-circuito-service.js?_t=' + ts,

			root + '/v1/spas/NCD/agendamento/consultar/consultar-agendamento-services.js?_t=' + ts,
			root + '/v1/spas/NCD/agendamento/consultar/consultar-agendamento-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/agendamento/consultar-realizados/consultar-agendamentos-realizados-services.js?_t=' + ts,
			root + '/v1/spas/NCD/agendamento/consultar-realizados/consultar-agendamentos-realizados-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/agendamento/detalhar-realizados/detalhar-agendamentos-realizados-services.js?_t=' + ts,
			root + '/v1/spas/NCD/agendamento/detalhar-realizados/detalhar-agendamentos-realizados-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/agendamento/solicitar/solicitar-agendamento-services.js?_t=' + ts,
			root + '/v1/spas/NCD/agendamento/solicitar/solicitar-agendamento-controller.js?_t=' + ts,

			root + '/v1/spas/NCD/pendencias/consultar/consultar-pendencias-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/pendencias/consultar/consultar-pendencias-services.js?_t=' + ts,
			root + '/v1/spas/NCD/pendencias/consultas-realizadas/consultar-pendencias-realizadas-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/pendencias/consultas-realizadas/consultar-pendencias-realizadas-services.js?_t=' + ts,
			root + '/v1/spas/NCD/pendencias/detalhar-realizados/detalhar-pendencias-realizadas-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/pendencias/detalhar-realizados/detalhar-pendencias-realizadas-services.js?_t=' + ts,
			root + '/v1/spas/NCD/pendencias/registrar/registrar-pendencias-controller.js?_t=' + ts,
			root + '/v1/spas/NCD/pendencias/registrar/registrar-pendencias-services.js?_t=' + ts,
			
			root + '/v1/spas/universal/viabilidade/registrar/registrar-viabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/universal/viabilidade/registrar/registrar-viabilidade-service.js?_t=' + ts,
			root + '/v1/spas/universal/viabilidade/consultar/consultar-viabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/universal/viabilidade/consultar/consultar-viabilidade-service.js?_t=' + ts,
			root + '/v1/spas/universal/viabilidade/consultar-registradas/consultar-registradas-controller.js?_t=' + ts,
			root + '/v1/spas/universal/viabilidade/consultar-registradas/consultar-registradas-service.js?_t=' + ts,
			root + '/v1/spas/universal/viabilidade/detalhar/detalhar-viabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/universal/viabilidade/detalhar/detalhar-viabilidade-service.js?_t=' + ts,

			root + '/v1/spas/universal/agendamento/solicitar/solicitar-agendamento-acc-controller.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/solicitar/solicitar-agendamento-acc-services.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/consultar/consultar-agendamento-acc-controller.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/consultar/consultar-agendamento-acc-services.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/detalhar-realizados/detalhar-agendamentos-realizados-universal-controller.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/detalhar-realizados/detalhar-agendamentos-realizados-universal-services.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/consultar-realizados/consultar-agendamentos-realizados-universal-controller.js?_t=' + ts,
			root + '/v1/spas/universal/agendamento/consultar-realizados/consultar-agendamentos-realizados-universal-services.js?_t=' + ts,

			root + '/v1/spas/universal/pendencias/consultar/consultar-pendencias-universal-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/consultar/consultar-pendencias-universal-services.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/registrar/solicitar-agendamento-pendencias-controller.js?_t='+ ts,
			root + '/v1/spas/universal/pendencias/registrar/solicitar-agendamento-pendencias-services.js?_t='+ ts,
			
			root + '/v1/spas/relatorios/agendamento/escolha-relatorios-agendamento-controller.js?_t=' + ts,
			root + '/v1/spas/relatorios/agendamento/relatorios-credenciamento-controller.js?_t=' + ts,
			root + '/v1/spas/relatorios/agendamento/relatorios-credenciamento-service.js?_t=' + ts,
			root + '/v1/spas/relatorios/pendencia/relatorios-credenciamento-controller.js?_t=' + ts,
			root + '/v1/spas/relatorios/pendencia/relatorios-credenciamento-service.js?_t=' + ts,

			root + '/v1/spas/universal/pendencias/registrar/solicitar-agendamento-pendencias-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/registrar/solicitar-agendamento-pendencias-services.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/consultas-realizadas/consultar-pendencias-realizadas-universal-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/consultas-realizadas/consultar-pendencias-realizadas-universal-services.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/detalhar-realizados/detalhar-pendencias-realizadas-universal-controller.js?_t=' + ts,
			root + '/v1/spas/universal/pendencias/detalhar-realizados/detalhar-pendencias-realizadas-universal-services.js?_t=' + ts,

			root + '/v1/spas/universal/utils/utils.js?_t=' + ts,

		]
	});
	PFNConfig.config({
		appName: 'QGD_Fornecedor_APP',
		jsFiles: [
			root + '/v1/spas/main-app-min.js?_t=' + ts
		]
	});

})(PFNConfig);
