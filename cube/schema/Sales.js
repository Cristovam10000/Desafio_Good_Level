cube(`Sales`, {
  sql: `SELECT * FROM public.sales`,

  measures: {
    count: {
      type: `count`,
      drillMembers: [id, createdAt, status, storeId, channelId]
    },

    totalAmount: {
      sql: `total_amount`,
      type: `sum`,
      format: `currency`
    },

    totalItemsValue: {
      sql: `total_amount_items`,
      type: `sum`,
      format: `currency`
    },

    averageTicket: {
      sql: `total_amount`,
      type: `avg`,
      format: `currency`
    },

    completedOrders: {
      type: `count`,
      filters: [
        { sql: `${CUBE}.sale_status_desc = 'COMPLETED'` }
      ]
    },

    cancelledOrders: {
      type: `count`,
      filters: [
        { sql: `${CUBE}.sale_status_desc = 'CANCELLED'` }
      ]
    }
  },

  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },

    status: {
      sql: `sale_status_desc`,
      type: `string`
    },

    storeId: {
      sql: `store_id`,
      type: `number`
    },

    channelId: {
      sql: `channel_id`,
      type: `number`
    },

    customerId: {
      sql: `customer_id`,
      type: `number`
    },

    createdAt: {
      sql: `created_at`,
      type: `time`
    },

    discountReason: {
      sql: `discount_reason`,
      type: `string`
    },

    origin: {
      sql: `origin`,
      type: `string`
    }
  },

  segments: {
    completed: {
      sql: `${CUBE}.sale_status_desc = 'COMPLETED'`
    },

    cancelled: {
      sql: `${CUBE}.sale_status_desc = 'CANCELLED'`
    }
  },

  preAggregations: {
    byDay: {
      type: `rollup`,
      measureReferences: [
        `count`,
        `totalAmount`,
        `totalItemsValue`,
        `averageTicket`,
        `completedOrders`,
        `cancelledOrders`
      ],
      timeDimensionReference: `createdAt`,
      granularity: `day`,
      partitionGranularity: `month`
    },

    byChannelStore: {
      type: `rollup`,
      measureReferences: [
        `totalAmount`,
        `completedOrders`,
        `cancelledOrders`
      ],
      dimensionReferences: [`storeId`, `channelId`],
      timeDimensionReference: `createdAt`,
      granularity: `day`,
      partitionGranularity: `month`
    }
  },

  refreshKey: {
    every: `10 minute`
  }
});
