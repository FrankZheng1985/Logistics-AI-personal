<?php
/**
 * 默认模板文件
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        <div class="blog-grid" style="display: grid; grid-template-columns: 1fr 300px; gap: var(--spacing-xl);">
            
            <!-- 文章列表 -->
            <div class="blog-main">
                <?php if (have_posts()) : ?>
                    
                    <?php if (is_search()) : ?>
                        <div class="search-results-header" style="margin-bottom: var(--spacing-xl);">
                            <h1><?php printf(__('搜索结果: %s', 'sysafari-logistics'), get_search_query()); ?></h1>
                        </div>
                    <?php elseif (is_archive()) : ?>
                        <div class="archive-header" style="margin-bottom: var(--spacing-xl);">
                            <?php the_archive_title('<h1>', '</h1>'); ?>
                            <?php the_archive_description('<p class="archive-description">', '</p>'); ?>
                        </div>
                    <?php endif; ?>
                    
                    <div class="posts-list">
                        <?php while (have_posts()) : the_post(); ?>
                            <article id="post-<?php the_ID(); ?>" <?php post_class('post-card'); ?> style="background: var(--color-white); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-md); margin-bottom: var(--spacing-lg);">
                                
                                <?php if (has_post_thumbnail()) : ?>
                                    <div class="post-card-image">
                                        <a href="<?php the_permalink(); ?>">
                                            <?php the_post_thumbnail('news-thumbnail', array('style' => 'width: 100%; height: 200px; object-fit: cover;')); ?>
                                        </a>
                                    </div>
                                <?php endif; ?>
                                
                                <div class="post-card-content" style="padding: var(--spacing-lg);">
                                    <div class="post-meta" style="font-size: 0.875rem; color: var(--color-gray); margin-bottom: var(--spacing-sm);">
                                        <span class="post-date"><i class="far fa-calendar-alt"></i> <?php echo get_the_date(); ?></span>
                                        <span class="post-author" style="margin-left: var(--spacing-md);"><i class="far fa-user"></i> <?php the_author(); ?></span>
                                        <?php if (has_category()) : ?>
                                            <span class="post-category" style="margin-left: var(--spacing-md);">
                                                <i class="far fa-folder"></i> <?php the_category(', '); ?>
                                            </span>
                                        <?php endif; ?>
                                    </div>
                                    
                                    <h2 class="post-title" style="margin-bottom: var(--spacing-sm);">
                                        <a href="<?php the_permalink(); ?>" style="color: var(--color-dark);"><?php the_title(); ?></a>
                                    </h2>
                                    
                                    <div class="post-excerpt" style="color: var(--color-gray-dark); margin-bottom: var(--spacing-md);">
                                        <?php the_excerpt(); ?>
                                    </div>
                                    
                                    <a href="<?php the_permalink(); ?>" class="btn btn-outline">
                                        <?php esc_html_e('阅读更多', 'sysafari-logistics'); ?>
                                        <i class="fas fa-arrow-right" style="margin-left: 8px;"></i>
                                    </a>
                                </div>
                            </article>
                        <?php endwhile; ?>
                    </div>
                    
                    <!-- 分页 -->
                    <div class="pagination" style="margin-top: var(--spacing-xl);">
                        <?php
                        the_posts_pagination(array(
                            'mid_size'  => 2,
                            'prev_text' => '<i class="fas fa-chevron-left"></i> ' . __('上一页', 'sysafari-logistics'),
                            'next_text' => __('下一页', 'sysafari-logistics') . ' <i class="fas fa-chevron-right"></i>',
                        ));
                        ?>
                    </div>
                    
                <?php else : ?>
                    
                    <div class="no-posts" style="text-align: center; padding: var(--spacing-3xl);">
                        <i class="fas fa-search" style="font-size: 4rem; color: var(--color-gray-light); margin-bottom: var(--spacing-lg);"></i>
                        <h2><?php esc_html_e('未找到内容', 'sysafari-logistics'); ?></h2>
                        <p style="color: var(--color-gray-dark);"><?php esc_html_e('抱歉，没有找到符合条件的内容，请尝试其他搜索词。', 'sysafari-logistics'); ?></p>
                        <a href="<?php echo esc_url(home_url('/')); ?>" class="btn btn-primary" style="margin-top: var(--spacing-lg);">
                            <?php esc_html_e('返回首页', 'sysafari-logistics'); ?>
                        </a>
                    </div>
                    
                <?php endif; ?>
            </div>
            
            <!-- 侧边栏 -->
            <aside class="blog-sidebar">
                <?php if (is_active_sidebar('sidebar-blog')) : ?>
                    <?php dynamic_sidebar('sidebar-blog'); ?>
                <?php else : ?>
                    
                    <!-- 搜索 -->
                    <div class="widget" style="background: var(--color-white); padding: var(--spacing-lg); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); margin-bottom: var(--spacing-lg);">
                        <h4 class="widget-title" style="margin-bottom: var(--spacing-md);"><?php esc_html_e('搜索', 'sysafari-logistics'); ?></h4>
                        <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>">
                            <div style="display: flex;">
                                <input type="search" name="s" class="form-control" placeholder="<?php esc_attr_e('搜索...', 'sysafari-logistics'); ?>" value="<?php echo get_search_query(); ?>" style="border-radius: var(--radius-md) 0 0 var(--radius-md);">
                                <button type="submit" class="btn btn-secondary" style="border-radius: 0 var(--radius-md) var(--radius-md) 0;">
                                    <i class="fas fa-search"></i>
                                </button>
                            </div>
                        </form>
                    </div>
                    
                    <!-- 分类 -->
                    <div class="widget" style="background: var(--color-white); padding: var(--spacing-lg); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); margin-bottom: var(--spacing-lg);">
                        <h4 class="widget-title" style="margin-bottom: var(--spacing-md);"><?php esc_html_e('分类', 'sysafari-logistics'); ?></h4>
                        <ul style="list-style: none; padding: 0; margin: 0;">
                            <?php
                            wp_list_categories(array(
                                'title_li' => '',
                                'style'    => 'list',
                            ));
                            ?>
                        </ul>
                    </div>
                    
                    <!-- 最近文章 -->
                    <div class="widget" style="background: var(--color-white); padding: var(--spacing-lg); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); margin-bottom: var(--spacing-lg);">
                        <h4 class="widget-title" style="margin-bottom: var(--spacing-md);"><?php esc_html_e('最近文章', 'sysafari-logistics'); ?></h4>
                        <ul style="list-style: none; padding: 0; margin: 0;">
                            <?php
                            $recent_posts = wp_get_recent_posts(array(
                                'numberposts' => 5,
                                'post_status' => 'publish',
                            ));
                            foreach ($recent_posts as $post) :
                            ?>
                                <li style="padding: var(--spacing-sm) 0; border-bottom: 1px solid var(--color-gray-light);">
                                    <a href="<?php echo get_permalink($post['ID']); ?>" style="color: var(--color-dark);">
                                        <?php echo esc_html($post['post_title']); ?>
                                    </a>
                                    <span style="display: block; font-size: 0.75rem; color: var(--color-gray);">
                                        <?php echo get_the_date('', $post['ID']); ?>
                                    </span>
                                </li>
                            <?php endforeach; wp_reset_postdata(); ?>
                        </ul>
                    </div>
                    
                <?php endif; ?>
            </aside>
        </div>
    </div>
</section>

<style>
.pagination {
    display: flex;
    justify-content: center;
}

.pagination .nav-links {
    display: flex;
    gap: var(--spacing-sm);
}

.pagination .page-numbers {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-white);
    border: 1px solid var(--color-gray-light);
    border-radius: var(--radius-sm);
    color: var(--color-dark);
}

.pagination .page-numbers.current,
.pagination .page-numbers:hover {
    background: var(--color-primary);
    border-color: var(--color-primary);
}

@media (max-width: 768px) {
    .blog-grid {
        grid-template-columns: 1fr !important;
    }
}
</style>

<?php
get_footer();
