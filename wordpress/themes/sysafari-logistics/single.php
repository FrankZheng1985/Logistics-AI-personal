<?php
/**
 * 单篇文章模板
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        <div class="blog-grid" style="display: grid; grid-template-columns: 1fr 300px; gap: var(--spacing-xl);">
            
            <!-- 文章内容 -->
            <div class="blog-main">
                <?php while (have_posts()) : the_post(); ?>
                    <article id="post-<?php the_ID(); ?>" <?php post_class('single-post'); ?>>
                        
                        <!-- 文章头部 -->
                        <header class="post-header" style="margin-bottom: var(--spacing-xl);">
                            <h1 style="font-size: 2rem; margin-bottom: var(--spacing-md);"><?php the_title(); ?></h1>
                            
                            <div class="post-meta" style="display: flex; flex-wrap: wrap; gap: var(--spacing-md); font-size: 0.875rem; color: var(--color-gray);">
                                <span class="post-date">
                                    <i class="far fa-calendar-alt"></i> <?php echo get_the_date(); ?>
                                </span>
                                <span class="post-author">
                                    <i class="far fa-user"></i> <?php the_author(); ?>
                                </span>
                                <?php if (has_category()) : ?>
                                    <span class="post-category">
                                        <i class="far fa-folder"></i> <?php the_category(', '); ?>
                                    </span>
                                <?php endif; ?>
                                <?php if (comments_open()) : ?>
                                    <span class="post-comments">
                                        <i class="far fa-comment"></i> <?php comments_number('0', '1', '%'); ?> 评论
                                    </span>
                                <?php endif; ?>
                            </div>
                        </header>
                        
                        <!-- 特色图片 -->
                        <?php if (has_post_thumbnail()) : ?>
                            <div class="post-thumbnail" style="margin-bottom: var(--spacing-xl); border-radius: var(--radius-lg); overflow: hidden;">
                                <?php the_post_thumbnail('large', array('style' => 'width: 100%; height: auto;')); ?>
                            </div>
                        <?php endif; ?>
                        
                        <!-- 文章内容 -->
                        <div class="post-content" style="font-size: 1.0625rem; line-height: 1.8; color: var(--color-dark);">
                            <?php the_content(); ?>
                            
                            <?php
                            // 分页链接
                            wp_link_pages(array(
                                'before' => '<div class="page-links" style="margin-top: var(--spacing-xl);">' . __('页面:', 'sysafari-logistics'),
                                'after'  => '</div>',
                            ));
                            ?>
                        </div>
                        
                        <!-- 标签 -->
                        <?php if (has_tag()) : ?>
                            <div class="post-tags" style="margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-gray-light);">
                                <strong><?php esc_html_e('标签:', 'sysafari-logistics'); ?></strong>
                                <?php the_tags('', ' ', ''); ?>
                            </div>
                        <?php endif; ?>
                        
                        <!-- 分享 -->
                        <div class="post-share" style="margin-top: var(--spacing-lg); display: flex; align-items: center; gap: var(--spacing-md);">
                            <strong><?php esc_html_e('分享:', 'sysafari-logistics'); ?></strong>
                            <a href="https://twitter.com/intent/tweet?url=<?php echo urlencode(get_permalink()); ?>&text=<?php echo urlencode(get_the_title()); ?>" target="_blank" rel="noopener" style="color: #1DA1F2;" title="分享到Twitter">
                                <i class="fab fa-twitter"></i>
                            </a>
                            <a href="https://www.facebook.com/sharer/sharer.php?u=<?php echo urlencode(get_permalink()); ?>" target="_blank" rel="noopener" style="color: #4267B2;" title="分享到Facebook">
                                <i class="fab fa-facebook-f"></i>
                            </a>
                            <a href="https://www.linkedin.com/shareArticle?mini=true&url=<?php echo urlencode(get_permalink()); ?>&title=<?php echo urlencode(get_the_title()); ?>" target="_blank" rel="noopener" style="color: #0077B5;" title="分享到LinkedIn">
                                <i class="fab fa-linkedin-in"></i>
                            </a>
                            <a href="javascript:void(0);" onclick="navigator.clipboard.writeText('<?php echo esc_js(get_permalink()); ?>'); alert('链接已复制!');" style="color: var(--color-gray);" title="复制链接">
                                <i class="fas fa-link"></i>
                            </a>
                        </div>
                        
                        <!-- 作者信息 -->
                        <div class="post-author-box" style="margin-top: var(--spacing-xl); padding: var(--spacing-xl); background: var(--color-light); border-radius: var(--radius-lg); display: flex; gap: var(--spacing-lg);">
                            <div class="author-avatar" style="width: 80px; height: 80px; min-width: 80px; border-radius: 50%; overflow: hidden;">
                                <?php echo get_avatar(get_the_author_meta('ID'), 80); ?>
                            </div>
                            <div class="author-info">
                                <h4 style="margin-bottom: var(--spacing-xs);"><?php the_author(); ?></h4>
                                <p style="color: var(--color-gray-dark); margin-bottom: 0;"><?php echo get_the_author_meta('description') ?: '暂无作者简介'; ?></p>
                            </div>
                        </div>
                        
                        <!-- 上下篇导航 -->
                        <nav class="post-navigation" style="margin-top: var(--spacing-xl); display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-lg);">
                            <?php
                            $prev_post = get_previous_post();
                            $next_post = get_next_post();
                            ?>
                            
                            <?php if ($prev_post) : ?>
                                <a href="<?php echo get_permalink($prev_post); ?>" class="prev-post" style="padding: var(--spacing-lg); background: var(--color-white); border: 1px solid var(--color-gray-light); border-radius: var(--radius-md); text-decoration: none;">
                                    <span style="font-size: 0.875rem; color: var(--color-gray);">
                                        <i class="fas fa-chevron-left"></i> <?php esc_html_e('上一篇', 'sysafari-logistics'); ?>
                                    </span>
                                    <span style="display: block; color: var(--color-dark); font-weight: 500; margin-top: var(--spacing-xs);">
                                        <?php echo esc_html($prev_post->post_title); ?>
                                    </span>
                                </a>
                            <?php else : ?>
                                <div></div>
                            <?php endif; ?>
                            
                            <?php if ($next_post) : ?>
                                <a href="<?php echo get_permalink($next_post); ?>" class="next-post" style="padding: var(--spacing-lg); background: var(--color-white); border: 1px solid var(--color-gray-light); border-radius: var(--radius-md); text-decoration: none; text-align: right;">
                                    <span style="font-size: 0.875rem; color: var(--color-gray);">
                                        <?php esc_html_e('下一篇', 'sysafari-logistics'); ?> <i class="fas fa-chevron-right"></i>
                                    </span>
                                    <span style="display: block; color: var(--color-dark); font-weight: 500; margin-top: var(--spacing-xs);">
                                        <?php echo esc_html($next_post->post_title); ?>
                                    </span>
                                </a>
                            <?php endif; ?>
                        </nav>
                        
                        <!-- 相关文章 -->
                        <?php
                        $related_posts = get_posts(array(
                            'category__in'   => wp_get_post_categories(get_the_ID()),
                            'post__not_in'   => array(get_the_ID()),
                            'posts_per_page' => 3,
                            'orderby'        => 'rand',
                        ));
                        
                        if ($related_posts) :
                        ?>
                            <div class="related-posts" style="margin-top: var(--spacing-2xl);">
                                <h3 style="margin-bottom: var(--spacing-lg);"><?php esc_html_e('相关文章', 'sysafari-logistics'); ?></h3>
                                <div class="related-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--spacing-lg);">
                                    <?php foreach ($related_posts as $post) : setup_postdata($post); ?>
                                        <article class="related-card" style="background: var(--color-white); border-radius: var(--radius-md); overflow: hidden; box-shadow: var(--shadow-sm);">
                                            <?php if (has_post_thumbnail()) : ?>
                                                <a href="<?php the_permalink(); ?>">
                                                    <?php the_post_thumbnail('thumbnail', array('style' => 'width: 100%; height: 120px; object-fit: cover;')); ?>
                                                </a>
                                            <?php endif; ?>
                                            <div style="padding: var(--spacing-md);">
                                                <h4 style="font-size: 0.875rem; margin-bottom: var(--spacing-xs);">
                                                    <a href="<?php the_permalink(); ?>" style="color: var(--color-dark);"><?php the_title(); ?></a>
                                                </h4>
                                                <span style="font-size: 0.75rem; color: var(--color-gray);"><?php echo get_the_date(); ?></span>
                                            </div>
                                        </article>
                                    <?php endforeach; wp_reset_postdata(); ?>
                                </div>
                            </div>
                        <?php endif; ?>
                        
                        <!-- 评论 -->
                        <?php if (comments_open() || get_comments_number()) : ?>
                            <div class="post-comments-section" style="margin-top: var(--spacing-2xl);">
                                <?php comments_template(); ?>
                            </div>
                        <?php endif; ?>
                        
                    </article>
                <?php endwhile; ?>
            </div>
            
            <!-- 侧边栏 -->
            <aside class="blog-sidebar">
                <?php get_template_part('template-parts/sidebar', 'blog'); ?>
            </aside>
        </div>
    </div>
</section>

<style>
.post-content h2 {
    margin-top: var(--spacing-xl);
    margin-bottom: var(--spacing-md);
}

.post-content h3 {
    margin-top: var(--spacing-lg);
    margin-bottom: var(--spacing-sm);
}

.post-content p {
    margin-bottom: var(--spacing-md);
}

.post-content img {
    max-width: 100%;
    height: auto;
    border-radius: var(--radius-md);
}

.post-content ul,
.post-content ol {
    margin-left: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
}

.post-content blockquote {
    border-left: 4px solid var(--color-primary);
    padding-left: var(--spacing-lg);
    margin: var(--spacing-lg) 0;
    font-style: italic;
    color: var(--color-gray-dark);
}

.post-content pre {
    background: var(--color-light);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    overflow-x: auto;
}

.post-content code {
    background: var(--color-light);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-family: monospace;
}

.post-tags a {
    display: inline-block;
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-light);
    border-radius: var(--radius-sm);
    margin-right: var(--spacing-xs);
    margin-bottom: var(--spacing-xs);
    color: var(--color-gray-dark);
    font-size: 0.875rem;
}

.post-tags a:hover {
    background: var(--color-primary);
    color: var(--color-dark);
}

@media (max-width: 768px) {
    .blog-grid {
        grid-template-columns: 1fr !important;
    }
    
    .related-grid {
        grid-template-columns: 1fr !important;
    }
    
    .post-navigation {
        grid-template-columns: 1fr !important;
    }
}
</style>

<?php
get_footer();
