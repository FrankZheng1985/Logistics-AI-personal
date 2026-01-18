<?php
/**
 * Template Name: 新闻资讯页面
 * 
 * 新闻资讯列表页面
 *
 * @package Sysafari_Logistics
 */

get_header();

// 分页
$paged = (get_query_var('paged')) ? get_query_var('paged') : 1;

// 分类筛选
$category_filter = isset($_GET['cat']) ? intval($_GET['cat']) : 0;

// 查询文章
$args = array(
    'post_type'      => 'post',
    'posts_per_page' => 9,
    'paged'          => $paged,
    'orderby'        => 'date',
    'order'          => 'DESC',
);

if ($category_filter) {
    $args['cat'] = $category_filter;
}

$news_query = new WP_Query($args);

// 获取分类
$categories = get_categories(array(
    'orderby' => 'count',
    'order'   => 'DESC',
    'number'  => 10,
));
?>

<div class="page-header">
    <div class="container">
        <h1><?php esc_html_e('新闻资讯', 'sysafari-logistics'); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        
        <!-- 分类筛选 -->
        <?php if ($categories) : ?>
            <div class="news-categories" style="display: flex; justify-content: center; gap: var(--spacing-sm); margin-bottom: var(--spacing-2xl); flex-wrap: wrap;">
                <a href="<?php echo esc_url(get_permalink()); ?>" 
                   class="category-btn <?php echo !$category_filter ? 'active' : ''; ?>"
                   style="padding: var(--spacing-sm) var(--spacing-md); border-radius: var(--radius-md); border: 1px solid var(--color-gray-light); color: var(--color-dark); text-decoration: none; transition: all var(--transition-fast); <?php echo !$category_filter ? 'background: var(--color-primary); border-color: var(--color-primary);' : ''; ?>">
                    <?php esc_html_e('全部', 'sysafari-logistics'); ?>
                </a>
                <?php foreach ($categories as $cat) : ?>
                    <a href="<?php echo esc_url(add_query_arg('cat', $cat->term_id, get_permalink())); ?>" 
                       class="category-btn <?php echo $category_filter == $cat->term_id ? 'active' : ''; ?>"
                       style="padding: var(--spacing-sm) var(--spacing-md); border-radius: var(--radius-md); border: 1px solid var(--color-gray-light); color: var(--color-dark); text-decoration: none; transition: all var(--transition-fast); <?php echo $category_filter == $cat->term_id ? 'background: var(--color-primary); border-color: var(--color-primary);' : ''; ?>">
                        <?php echo esc_html($cat->name); ?>
                        <span style="color: var(--color-gray); font-size: 0.75rem;">(<?php echo $cat->count; ?>)</span>
                    </a>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>
        
        <!-- 新闻列表 -->
        <?php if ($news_query->have_posts()) : ?>
            <div class="news-grid">
                <?php while ($news_query->have_posts()) : $news_query->the_post(); ?>
                    <article class="news-card">
                        <?php if (has_post_thumbnail()) : ?>
                            <div class="news-card-image">
                                <a href="<?php the_permalink(); ?>">
                                    <?php the_post_thumbnail('news-thumbnail'); ?>
                                </a>
                            </div>
                        <?php else : ?>
                            <div class="news-card-image" style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);">
                                <a href="<?php the_permalink(); ?>" style="display: block; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;">
                                    <i class="fas fa-newspaper" style="font-size: 3rem; color: rgba(255,255,255,0.5);"></i>
                                </a>
                            </div>
                        <?php endif; ?>
                        
                        <div class="news-card-content">
                            <div class="news-card-meta" style="display: flex; gap: var(--spacing-md); margin-bottom: var(--spacing-sm); font-size: 0.75rem; color: var(--color-gray);">
                                <span class="news-card-date">
                                    <i class="far fa-calendar-alt"></i>
                                    <?php echo get_the_date(); ?>
                                </span>
                                <?php
                                $post_categories = get_the_category();
                                if ($post_categories) :
                                ?>
                                    <span class="news-card-category">
                                        <i class="far fa-folder"></i>
                                        <?php echo esc_html($post_categories[0]->name); ?>
                                    </span>
                                <?php endif; ?>
                            </div>
                            
                            <h3 class="news-card-title">
                                <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                            </h3>
                            
                            <p class="news-card-excerpt"><?php echo wp_trim_words(get_the_excerpt(), 25); ?></p>
                            
                            <a href="<?php the_permalink(); ?>" class="news-card-link" style="display: inline-flex; align-items: center; gap: 5px; color: var(--color-secondary); font-weight: 500; font-size: 0.875rem;">
                                <?php esc_html_e('阅读更多', 'sysafari-logistics'); ?>
                                <i class="fas fa-arrow-right"></i>
                            </a>
                        </div>
                    </article>
                <?php endwhile; ?>
            </div>
            
            <!-- 分页 -->
            <?php if ($news_query->max_num_pages > 1) : ?>
                <div class="news-pagination" style="margin-top: var(--spacing-2xl);">
                    <?php
                    echo paginate_links(array(
                        'total'     => $news_query->max_num_pages,
                        'current'   => $paged,
                        'prev_text' => '<i class="fas fa-chevron-left"></i> ' . __('上一页', 'sysafari-logistics'),
                        'next_text' => __('下一页', 'sysafari-logistics') . ' <i class="fas fa-chevron-right"></i>',
                    ));
                    ?>
                </div>
            <?php endif; ?>
            
            <?php wp_reset_postdata(); ?>
            
        <?php else : ?>
            <div class="no-news" style="text-align: center; padding: var(--spacing-3xl);">
                <i class="fas fa-newspaper" style="font-size: 4rem; color: var(--color-gray-light); margin-bottom: var(--spacing-lg);"></i>
                <h2><?php esc_html_e('暂无新闻', 'sysafari-logistics'); ?></h2>
                <p style="color: var(--color-gray-dark);"><?php esc_html_e('敬请期待更多精彩内容', 'sysafari-logistics'); ?></p>
            </div>
        <?php endif; ?>
        
    </div>
</section>

<!-- 订阅区域 -->
<section class="section" style="background: var(--color-light);">
    <div class="container">
        <div style="max-width: 600px; margin: 0 auto; text-align: center;">
            <h2 style="margin-bottom: var(--spacing-md);"><?php esc_html_e('订阅最新资讯', 'sysafari-logistics'); ?></h2>
            <p style="color: var(--color-gray-dark); margin-bottom: var(--spacing-xl);">
                <?php esc_html_e('订阅我们的邮件通讯，及时获取行业动态、物流政策和公司最新消息', 'sysafari-logistics'); ?>
            </p>
            <form class="subscribe-form" style="display: flex; gap: var(--spacing-sm);">
                <input type="email" placeholder="<?php esc_attr_e('输入您的邮箱地址', 'sysafari-logistics'); ?>" style="flex: 1; padding: var(--spacing-md); border: 1px solid var(--color-gray-light); border-radius: var(--radius-md); font-size: 1rem;">
                <button type="submit" class="btn btn-secondary">
                    <?php esc_html_e('订阅', 'sysafari-logistics'); ?>
                </button>
            </form>
        </div>
    </div>
</section>

<style>
.category-btn:hover {
    background: var(--color-primary);
    border-color: var(--color-primary);
}

.news-card-image {
    aspect-ratio: 16/9;
    overflow: hidden;
}

.news-card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.news-pagination {
    display: flex;
    justify-content: center;
}

.news-pagination .page-numbers {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-white);
    border: 1px solid var(--color-gray-light);
    border-radius: var(--radius-sm);
    color: var(--color-dark);
    margin: 0 var(--spacing-xs);
}

.news-pagination .page-numbers.current,
.news-pagination .page-numbers:hover {
    background: var(--color-primary);
    border-color: var(--color-primary);
}

@media (max-width: 768px) {
    .subscribe-form {
        flex-direction: column;
    }
}
</style>

<?php
get_footer();
