cube(`ProductSales`, {
  sql: `
    SELECT
      ps.id,
      ps.sale_id,
      ps.product_id,
      ps.quantity,
      ps.total_price,
      ps.base_price,
      s.created_at,
      s.store_id,
      s.channel_id,
      p.name AS product_name
    FROM public.product_sales ps
    JOIN public.sales s ON s.id = ps.sale_id
    JOIN public.products p ON p.id = ps.product_id
    WHERE s.sale_status_desc = 'COMPLETED'
  `,

  joins: {
    Sales: {
      sql: `${CUBE}.sale_id = ${Sales}.id`,
      relationship: `belongsTo`
    }
  },

  measures: {
    qty: {
      sql: `quantity`,
      type: `sum`
    },

    revenue: {
      sql: `total_price`,
      type: `sum`,
      format: `currency`
    },

    baseRevenue: {
      sql: `base_price * quantity`,
      type: `sum`,
      format: `currency`
    },

    orders: {
      sql: `sale_id`,
      type: `countDistinct`
    },

    avgRevenuePerOrder: {
      sql: `total_price`,
      type: `avg`,
      format: `currency`
    }
  },

  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },

    saleId: {
      sql: `sale_id`,
      type: `number`
    },

    productId: {
      sql: `product_id`,
      type: `number`
    },

    productName: {
      sql: `product_name`,
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

    createdAt: {
      sql: `created_at`,
      type: `time`
    }
  },

  preAggregations: {
    byDayProduct: {
      type: `rollup`,
      measureReferences: [
        `qty`,
        `revenue`,
        `baseRevenue`,
        `orders`
      ],
      dimensionReferences: [`productId`, `productName`],
      timeDimensionReference: `createdAt`,
      granularity: `day`,
      partitionGranularity: `month`
    },

    byStoreChannel: {
      type: `rollup`,
      measureReferences: [`revenue`, `qty`, `orders`],
      dimensionReferences: [`storeId`, `channelId`],
      timeDimensionReference: `createdAt`,
      granularity: `day`,
      partitionGranularity: `month`
    }
  },

  refreshKey: {
    every: `15 minute`
  }
});
