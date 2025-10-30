cube(`Delivery`, {
  sql: `
    SELECT
      s.id,
      s.store_id,
      s.channel_id,
      s.created_at,
      s.delivery_seconds,
      s.production_seconds,
      da.city,
      da.neighborhood
    FROM public.sales s
    JOIN public.delivery_addresses da ON da.sale_id = s.id
    WHERE s.sale_status_desc = 'COMPLETED'
      AND s.delivery_seconds IS NOT NULL
  `,

  measures: {
    deliveries: {
      sql: `id`,
      type: `countDistinct`
    },

    avgDeliveryMinutes: {
      sql: `delivery_seconds / 60.0`,
      type: `avg`
    },

    avgProductionMinutes: {
      sql: `production_seconds / 60.0`,
      type: `avg`
    },

    p90DeliveryMinutes: {
      sql: `PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY ${CUBE}.delivery_seconds / 60.0)`,
      type: `number`
    }
  },

  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },

    storeId: {
      sql: `store_id`,
      type: `number`
    },

    channelId: {
      sql: `channel_id`,
      type: `number`
    },

    city: {
      sql: `city`,
      type: `string`
    },

    neighborhood: {
      sql: `neighborhood`,
      type: `string`
    },

    createdAt: {
      sql: `created_at`,
      type: `time`
    }
  },

  preAggregations: {
    byAreaDay: {
      type: `rollup`,
      measureReferences: [`deliveries`, `avgDeliveryMinutes`, `avgProductionMinutes`],
      dimensionReferences: [`city`, `neighborhood`],
      timeDimensionReference: `createdAt`,
      granularity: `day`,
      partitionGranularity: `month`
    },

    byStoreChannel: {
      type: `rollup`,
      measureReferences: [`deliveries`, `avgDeliveryMinutes`],
      dimensionReferences: [`storeId`, `channelId`],
      timeDimensionReference: `createdAt`,
      granularity: `day`,
      partitionGranularity: `month`
    }
  },

  refreshKey: {
    every: `30 minute`
  }
});
