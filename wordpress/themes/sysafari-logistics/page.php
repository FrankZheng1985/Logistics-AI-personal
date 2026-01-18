<?php
/**
 * 默认页面模板
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<?php if (!is_front_page()) : ?>
<div class="page-header">
    <div class="container">
        <h1><?php the_title(); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>
<?php endif; ?>

<section class="section page-content">
    <div class="container">
        <?php while (have_posts()) : the_post(); ?>
            <article id="page-<?php the_ID(); ?>" <?php post_class(); ?>>
                <?php if (has_post_thumbnail() && !is_front_page()) : ?>
                    <div class="page-thumbnail" style="margin-bottom: var(--spacing-xl); border-radius: var(--radius-lg); overflow: hidden;">
                        <?php the_post_thumbnail('large', array('style' => 'width: 100%; height: auto;')); ?>
                    </div>
                <?php endif; ?>
                
                <div class="page-entry-content">
                    <?php the_content(); ?>
                </div>
                
                <?php
                wp_link_pages(array(
                    'before' => '<div class="page-links" style="margin-top: var(--spacing-xl);">' . __('页面:', 'sysafari-logistics'),
                    'after'  => '</div>',
                ));
                ?>
            </article>
            
            <?php if (comments_open() || get_comments_number()) : ?>
                <div class="page-comments" style="margin-top: var(--spacing-2xl);">
                    <?php comments_template(); ?>
                </div>
            <?php endif; ?>
        <?php endwhile; ?>
    </div>
</section>

<?php
get_footer();
