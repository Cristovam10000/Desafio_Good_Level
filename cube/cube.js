module.exports = {
  scheduledRefreshTimer: true,
  contextToAppId: () => `default`,
  http: {
    cors: {
      origin: '*',
      methods: 'GET,POST',
      allowedHeaders: '*'
    }
  },
  preAggregationsSchema: 'cube_preaggs'
};
